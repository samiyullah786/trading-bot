from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any


PROTOCOL_VERSION = "1.0"


@dataclass(frozen=True)
class ServerRequest:
    request_id: str
    operation: str
    payload: dict[str, Any] = field(default_factory=dict)
    protocol_version: str = PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        if not self.request_id.strip() or not self.operation.strip():
            raise ValueError("request_id and operation are required")
        return {"v": self.protocol_version, "id": self.request_id, "op": self.operation, "payload": self.payload}

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ServerRequest":
        if len(raw) > 1_000_000:
            raise ValueError("request exceeds protocol limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid request encoding") from exc
        if not isinstance(value, dict) or value.get("v") != PROTOCOL_VERSION:
            raise ValueError("unsupported protocol version")
        payload = value.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return cls(str(value.get("id", "")), str(value.get("op", "")), payload, str(value["v"]))


@dataclass(frozen=True)
class ServerResponse:
    request_id: str
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    protocol_version: str = PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"v": self.protocol_version, "id": self.request_id, "ok": self.ok, "result": self.result}
        if self.error is not None:
            body["error"] = self.error
        return body

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ServerResponse":
        if not isinstance(value, dict) or value.get("v") != PROTOCOL_VERSION:
            raise ValueError("unsupported protocol version")
        result = value.get("result", {})
        if not isinstance(result, dict):
            raise ValueError("result must be an object")
        error = value.get("error")
        if error is not None and not isinstance(error, str):
            raise ValueError("error must be a string")
        return cls(str(value.get("id", "")), bool(value.get("ok")), result, error, str(value["v"]))

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ServerResponse":
        if len(raw) > 2_000_000:
            raise ValueError("response exceeds protocol limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid response encoding") from exc
        return cls.from_dict(value)


def new_request_id() -> str:
    return secrets.token_hex(16)
