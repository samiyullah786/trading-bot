from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class CdpTarget:
    id: str
    websocket_url: str
    title: str = ""
    url: str = ""


class CdpProtocolError(RuntimeError):
    pass


class ChromeDevTools:
    """Dependency-free CDP client with target selection and lifecycle primitives."""

    def __init__(self, endpoint: str = "http://127.0.0.1:9222", timeout: float = 15.0):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("endpoint must be an HTTP(S) URL")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def targets(self) -> list[CdpTarget]:
        with urllib.request.urlopen(self.endpoint + "/json", timeout=self.timeout) as response:
            rows = json.loads(response.read().decode("utf-8"))
        return [CdpTarget(r["id"], r["webSocketDebuggerUrl"], r.get("title", ""), r.get("url", ""))
                for r in rows if r.get("type") == "page" and r.get("webSocketDebuggerUrl")]

    def select_target(self, target_id: str | None = None, url_contains: str | None = None) -> CdpTarget:
        targets = self.targets()
        if target_id:
            for target in targets:
                if target.id == target_id:
                    return target
            raise CdpProtocolError(f"target not found: {target_id}")
        if url_contains:
            matches = [target for target in targets if url_contains in target.url]
            if matches:
                return matches[0]
            raise CdpProtocolError(f"no target URL contains: {url_contains}")
        if not targets:
            raise CdpProtocolError("no page targets available")
        return targets[0]

    def _connect(self, websocket_url: str):
        parsed = urlparse(websocket_url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            raise ValueError("CDP endpoint must be ws:// or wss://")
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        raw = socket.create_connection((parsed.hostname, port), timeout=self.timeout)
        sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname) if parsed.scheme == "wss" else raw
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f"GET {path} HTTP/1.1\r\nHost: {parsed.hostname}:{port}\r\n"
                   f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                   "Sec-WebSocket-Version: 13\r\n\r\n")
        sock.sendall(request.encode())
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = sock.recv(4096)
            if not chunk:
                raise CdpProtocolError("websocket handshake closed")
            header += chunk
            if len(header) > 65536:
                raise CdpProtocolError("invalid websocket handshake")
        first_line = header.split(b"\r\n", 1)[0]
        if b" 101 " not in first_line:
            raise CdpProtocolError("CDP websocket handshake failed")
        return sock

    @staticmethod
    def _frame(payload: bytes) -> bytes:
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            head = bytes([0x81, 0x80 | n])
        elif n < 65536:
            head = bytes([0x81, 0x80 | 126]) + struct.pack("!H", n)
        else:
            head = bytes([0x81, 0x80 | 127]) + struct.pack("!Q", n)
        return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    @staticmethod
    def _read(sock: socket.socket) -> bytes:
        def recv_exact(n):
            data = b""
            while len(data) < n:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    raise CdpProtocolError("websocket closed")
                data += chunk
            return data
        while True:
            first = recv_exact(2)
            opcode = first[0] & 0x0F
            length = first[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", recv_exact(8))[0]
            if length > 16 * 1024 * 1024:
                raise CdpProtocolError("websocket frame too large")
            masked = bool(first[1] & 0x80)
            mask = recv_exact(4) if masked else b""
            data = recv_exact(length)
            if masked:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x8:
                raise CdpProtocolError("websocket closed by browser")
            if opcode == 0x9:
                continue
            if opcode == 0x1:
                return data

    def command(self, target: CdpTarget, method: str, params: dict | None = None) -> dict:
        sock = self._connect(target.websocket_url)
        try:
            payload = json.dumps({"id": 1, "method": method, "params": params or {}}).encode()
            sock.sendall(self._frame(payload))
            while True:
                result = json.loads(self._read(sock).decode())
                if result.get("id") != 1:
                    continue
                if "error" in result:
                    raise CdpProtocolError(json.dumps(result["error"], sort_keys=True))
                return result.get("result", {})
        finally:
            sock.close()

    def navigate(self, target: CdpTarget, url: str) -> dict:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("browser navigation requires http(s)")
        return self.command(target, "Page.navigate", {"url": url})

    def evaluate(self, target: CdpTarget, expression: str, return_by_value: bool = True) -> object:
        result = self.command(target, "Runtime.evaluate", {"expression": expression, "returnByValue": return_by_value, "awaitPromise": True})
        remote = result.get("result", {})
        if remote.get("subtype") == "error":
            raise CdpProtocolError(remote.get("description", "JavaScript evaluation failed"))
        return remote.get("value", remote.get("description"))

    def screenshot_png(self, target: CdpTarget) -> bytes:
        result = self.command(target, "Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])
