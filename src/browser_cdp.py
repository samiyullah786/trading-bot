from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import urllib.request
import uuid
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
    """Small dependency-free Chrome DevTools Protocol client.

    It intentionally implements only the primitives AUREON needs for controlled
    browser work: target discovery, navigation, JavaScript evaluation and
    screenshots. No browser automation framework is used.
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:9222", timeout: float = 15.0):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("endpoint must be an HTTP(S) URL")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def targets(self) -> list[CdpTarget]:
        with urllib.request.urlopen(self.endpoint + "/json", timeout=self.timeout) as response:
            rows = json.loads(response.read().decode("utf-8"))
        return [CdpTarget(r["id"], r["webSocketDebuggerUrl"], r.get("title", ""), r.get("url", ""))
                for r in rows if r.get("type") == "page" and r.get("webSocketDebuggerUrl")]

    def _connect(self, websocket_url: str):
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws" or not parsed.hostname:
            raise ValueError("only ws:// CDP endpoints are supported")
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        sock = socket.create_connection((parsed.hostname, port), timeout=self.timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f"GET {path} HTTP/1.1\r\nHost: {parsed.hostname}:{port}\r\n"
                   f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                   "Sec-WebSocket-Version: 13\r\n\r\n")
        sock.sendall(request.encode())
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = sock.recv(4096)
            if not chunk: raise CdpProtocolError("websocket handshake closed")
            header += chunk
            if len(header) > 65536: raise CdpProtocolError("invalid websocket handshake")
        if b" 101 " not in header.split(b"\r\n", 1)[0]:
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
                if not chunk: raise CdpProtocolError("websocket closed")
                data += chunk
            return data
        first = recv_exact(2)
        opcode = first[0] & 0x0F
        length = first[1] & 0x7F
        if length == 126: length = struct.unpack("!H", recv_exact(2))[0]
        elif length == 127: length = struct.unpack("!Q", recv_exact(8))[0]
        data = recv_exact(length)
        if opcode == 0x8: raise CdpProtocolError("websocket closed by browser")
        if opcode != 0x1: return ChromeDevTools._read(sock)
        return data

    def command(self, target: CdpTarget, method: str, params: dict | None = None) -> dict:
        sock = self._connect(target.websocket_url)
        try:
            message_id = 1
            payload = json.dumps({"id": message_id, "method": method, "params": params or {}}).encode()
            sock.sendall(self._frame(payload))
            while True:
                result = json.loads(self._read(sock).decode())
                if result.get("id") != message_id:
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
        result = self.command(target, "Runtime.evaluate", {"expression": expression, "returnByValue": return_by_value})
        remote = result.get("result", {})
        if remote.get("subtype") == "error" or remote.get("description") and remote.get("type") == "object" and remote.get("objectId") is None:
            raise CdpProtocolError(remote.get("description", "JavaScript evaluation failed"))
        return remote.get("value", remote.get("description"))

    def screenshot_png(self, target: CdpTarget) -> bytes:
        result = self.command(target, "Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])
