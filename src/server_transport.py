from __future__ import annotations

import socket
import socketserver
from typing import Callable

from .server_protocol import ServerRequest, ServerResponse


class LengthPrefixedCodec:
    MAX_FRAME = 2_000_000

    @classmethod
    def read(cls, stream) -> bytes:
        header = stream.read(4)
        if len(header) != 4:
            raise ConnectionError("incomplete frame header")
        size = int.from_bytes(header, "big")
        if size <= 0 or size > cls.MAX_FRAME:
            raise ValueError("invalid frame size")
        payload = stream.read(size)
        if len(payload) != size:
            raise ConnectionError("incomplete frame")
        return payload

    @classmethod
    def write(cls, stream, payload: bytes) -> None:
        if not payload or len(payload) > cls.MAX_FRAME:
            raise ValueError("invalid frame payload")
        stream.write(len(payload).to_bytes(4, "big") + payload)
        stream.flush()


class AUREONRequestHandler(socketserver.StreamRequestHandler):
    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(self.server.request_timeout)  # type: ignore[attr-defined]

    def handle(self) -> None:
        service: Callable[[ServerRequest], ServerResponse] = self.server.service  # type: ignore[attr-defined]
        try:
            request = ServerRequest.from_bytes(LengthPrefixedCodec.read(self.rfile))
            response = service(request)
        except Exception:
            response = ServerResponse("", False, error="PROTOCOL_ERROR")
        try:
            LengthPrefixedCodec.write(self.wfile, response.to_bytes())
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return


class BoundedThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], handler, *, max_connections: int, request_timeout: float) -> None:
        if max_connections < 1:
            raise ValueError("max_connections must be positive")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        self.request_timeout = request_timeout
        self._connection_slots = __import__("threading").BoundedSemaphore(max_connections)
        super().__init__(address, handler)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def process_request(self, request, client_address) -> None:
        if not self._connection_slots.acquire(blocking=False):
            try:
                request.close()
            finally:
                return
        def run() -> None:
            try:
                self.finish_request(request, client_address)
                self.shutdown_request(request)
            finally:
                self._connection_slots.release()
        thread = __import__("threading").Thread(target=run, daemon=True)
        thread.start()


class AUREONServer(BoundedThreadingTCPServer):
    """Bounded local/remote transport; remote deployment should add TLS at the socket boundary."""

    def __init__(self, address: tuple[str, int], service: Callable[[ServerRequest], ServerResponse], *, max_connections: int = 64, request_timeout: float = 15.0) -> None:
        self.service = service
        super().__init__(address, AUREONRequestHandler, max_connections=max_connections, request_timeout=request_timeout)
