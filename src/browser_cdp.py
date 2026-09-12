from __future__ import annotations

import base64
import ipaddress
import json
import os
import socket
import ssl
import struct
import time
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


class BrowserConnectionError(CdpProtocolError):
    """The browser transport disappeared; the caller must re-discover the target."""


class ChromeDevTools:
    """Dependency-free CDP client with bounded browser interaction primitives."""

    def __init__(self, endpoint: str = "http://127.0.0.1:9222", timeout: float = 15.0):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("endpoint must be an HTTP(S) URL")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def targets(self) -> list[CdpTarget]:
        try:
            with urllib.request.urlopen(self.endpoint + "/json", timeout=self.timeout) as response:
                rows = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise BrowserConnectionError(f"browser target discovery failed: {type(exc).__name__}") from exc
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
        try:
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
                    raise BrowserConnectionError("websocket handshake closed")
                header += chunk
                if len(header) > 65536:
                    raise BrowserConnectionError("invalid websocket handshake")
            if b" 101 " not in header.split(b"\r\n", 1)[0]:
                raise BrowserConnectionError("CDP websocket handshake failed")
            return sock
        except BrowserConnectionError:
            raise
        except OSError as exc:
            raise BrowserConnectionError(f"CDP transport unavailable: {type(exc).__name__}") from exc

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
                    raise BrowserConnectionError("websocket closed")
                data += chunk
            return data

        fragments: list[bytes] = []
        fragmented = False
        while True:
            first = recv_exact(2)
            fin = bool(first[0] & 0x80)
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
                raise BrowserConnectionError("websocket closed by browser")
            if opcode == 0x9:
                pong = bytes([0x8A, len(data)]) + data
                try:
                    sock.sendall(pong)
                except OSError:
                    pass
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x0:
                if not fragmented:
                    raise CdpProtocolError("unexpected websocket continuation")
                fragments.append(data)
                if fin:
                    return b"".join(fragments)
                continue
            if opcode not in {0x1, 0x2}:
                continue
            fragments = [data]
            fragmented = not fin
            if fin:
                return data

    def command(self, target: CdpTarget, method: str, params: dict | None = None) -> dict:
        sock = self._connect(target.websocket_url)
        try:
            payload = json.dumps({"id": 1, "method": method, "params": params or {}}).encode()
            try:
                sock.sendall(self._frame(payload))
                while True:
                    result = json.loads(self._read(sock).decode())
                    if result.get("id") != 1:
                        continue
                    if "error" in result:
                        raise CdpProtocolError(json.dumps(result["error"], sort_keys=True))
                    return result.get("result", {})
            except BrowserConnectionError:
                raise
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise BrowserConnectionError(f"CDP command transport failed: {type(exc).__name__}") from exc
        finally:
            sock.close()

    def navigate(self, target: CdpTarget, url: str) -> dict:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("browser navigation requires an absolute http(s) URL")
        return self.command(target, "Page.navigate", {"url": url})

    def evaluate(self, target: CdpTarget, expression: str, return_by_value: bool = True) -> object:
        if not expression or len(expression.encode("utf-8")) > 256_000:
            raise ValueError("JavaScript expression is empty or too large")
        result = self.command(target, "Runtime.evaluate", {"expression": expression, "returnByValue": return_by_value, "awaitPromise": True})
        remote = result.get("result", {})
        if remote.get("subtype") == "error" or remote.get("type") == "error":
            raise CdpProtocolError(remote.get("description", "JavaScript evaluation failed"))
        return remote.get("value", remote.get("description"))

    def click(self, target: CdpTarget, selector: str) -> object:
        if not selector or len(selector) > 4096:
            raise ValueError("selector must be non-empty and bounded")
        expression = "(() => { const e=document.querySelector(%s); if(!e) throw new Error('element not found'); e.scrollIntoView({block:'center'}); e.click(); return {tag:e.tagName,text:(e.innerText||'').slice(0,1000)}; })()" % json.dumps(selector)
        return self.evaluate(target, expression)

    def focus(self, target: CdpTarget, selector: str) -> object:
        if not selector or len(selector) > 4096:
            raise ValueError("selector must be non-empty and bounded")
        expression = "(() => { const e=document.querySelector(%s); if(!e) throw new Error('element not found'); e.focus(); return true; })()" % json.dumps(selector)
        return self.evaluate(target, expression)

    def fill(self, target: CdpTarget, selector: str, text: str) -> object:
        if not selector or len(selector) > 4096:
            raise ValueError("selector must be non-empty and bounded")
        if len(text.encode("utf-8")) > 65536:
            raise ValueError("text input too large")
        expression = "(() => { const e=document.querySelector(%s); if(!e) throw new Error('element not found'); e.focus(); const v=%s; const proto=Object.getPrototypeOf(e); const d=Object.getOwnPropertyDescriptor(proto,'value'); if(d&&d.set)d.set.call(e,v); else e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return {tag:e.tagName,valueLength:v.length}; })()" % (json.dumps(selector), json.dumps(text))
        return self.evaluate(target, expression)

    def type_text(self, target: CdpTarget, text: str) -> dict:
        if len(text.encode("utf-8")) > 65536:
            raise ValueError("text input too large")
        self.command(target, "Input.insertText", {"text": text})
        return {"inserted_bytes": len(text.encode("utf-8"))}

    def press_key(self, target: CdpTarget, key: str) -> dict:
        if not key or len(key) > 64:
            raise ValueError("key must be bounded")
        self.command(target, "Input.dispatchKeyEvent", {"type": "keyDown", "key": key})
        self.command(target, "Input.dispatchKeyEvent", {"type": "keyUp", "key": key})
        return {"key": key}

    def scroll(self, target: CdpTarget, x: int = 0, y: int = 600) -> object:
        x = max(-100_000, min(100_000, int(x)))
        y = max(-100_000, min(100_000, int(y)))
        return self.evaluate(target, f"window.scrollBy({x},{y}); ({x},{y})")

    def wait_for(self, target: CdpTarget, selector: str, timeout: float | None = None, interval: float = 0.1) -> object:
        if not selector or len(selector) > 4096:
            raise ValueError("selector must be non-empty and bounded")
        limit = self.timeout if timeout is None else float(timeout)
        if limit <= 0 or limit > 120:
            raise ValueError("wait timeout must be between 0 and 120 seconds")
        interval = max(0.05, min(float(interval), 2.0))
        deadline = time.monotonic() + limit
        expression = "Boolean(document.querySelector(%s))" % json.dumps(selector)
        while time.monotonic() < deadline:
            if bool(self.evaluate(target, expression)):
                return {"selector": selector, "found": True}
            time.sleep(interval)
        raise TimeoutError(f"selector not found before timeout: {selector}")

    def dom_snapshot(self, target: CdpTarget, max_chars: int = 50000) -> str:
        max_chars = max(1, min(int(max_chars), 200000))
        expression = "(() => { const root=document.documentElement; if(!root) return ''; return root.outerHTML; })()"
        return str(self.evaluate(target, expression) or "")[:max_chars]

    def accessibility_snapshot(self, target: CdpTarget, max_chars: int = 50000) -> object:
        result = self.command(target, "Accessibility.getFullAXTree", {})
        text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        return text[:max(1, min(int(max_chars), 200000))]

    def back(self, target: CdpTarget) -> object:
        return self.evaluate(target, "history.back(); true")

    def forward(self, target: CdpTarget) -> object:
        return self.evaluate(target, "history.forward(); true")

    def reload(self, target: CdpTarget) -> dict:
        return self.command(target, "Page.reload", {"ignoreCache": False})

    def page_text(self, target: CdpTarget, max_chars: int = 20000) -> str:
        max_chars = max(1, min(max_chars, 200000))
        value = self.evaluate(target, "document.body ? document.body.innerText : ''")
        return str(value or "")[:max_chars]

    def screenshot_png(self, target: CdpTarget) -> bytes:
        result = self.command(target, "Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])
