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
    def handle(self) -> None:
        service: Callable[[ServerRequest], ServerResponse] = self.server.service  # type: ignore[attr-defined]
        try:
            request = ServerRequest.from_bytes(LengthPrefixedCodec.read(self.rfile))
            response = service(request)
        except Exception as exc:
            response = ServerResponse("", False, error=f"protocol error: {type(exc).__name__}")
        LengthPrefixedCodec.write(self.wfile, response.to_bytes())


class AUREONServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: Callable[[ServerRequest], ServerResponse]) -> None:
        super().__init__(address, AUREONRequestHandler)
        self.service = service
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
