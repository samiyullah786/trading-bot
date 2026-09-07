from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import re
import time
from typing import Any, Iterable


_SECRET_KEY = re.compile(r"(password|passwd|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)", re.I)
_SECRET_VALUE = re.compile(r"(?i)\b(?:bearer\s+)?[A-Za-z0-9_\-]{24,}\b")
_MAX_STRING = 4096
_MAX_PAYLOAD_BYTES = 64 * 1024


@dataclass(frozen=True)
class Event:
    sequence: int
    event_type: str
    payload: dict[str, Any]
    timestamp: float
    previous_hash: str
    hash: str


class EventStore:
    """Dependency-free durable append-only event log with integrity controls."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _canonical(sequence: int, event_type: str, payload: dict[str, Any], timestamp: float, previous_hash: str) -> bytes:
        return json.dumps({"sequence": sequence, "event_type": event_type, "payload": payload,
                           "timestamp": timestamp, "previous_hash": previous_hash},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @classmethod
    def _sanitize(cls, value: Any, key: str | None = None) -> Any:
        if key and _SECRET_KEY.search(key):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(k): cls._sanitize(v, str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(v) for v in value]
        if isinstance(value, str):
            value = value[:_MAX_STRING]
            return _SECRET_VALUE.sub("[REDACTED]", value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)[:_MAX_STRING]

    @classmethod
    def _bounded_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        sanitized = cls._sanitize(dict(payload))
        encoded = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if len(encoded) <= _MAX_PAYLOAD_BYTES:
            return sanitized
        return {"_payload_truncated": True, "_payload_sha256": hashlib.sha256(encoded).hexdigest(),
                "_payload_size": len(encoded)}

    def _read(self) -> list[Event]:
        if not self.path.exists():
            return []
        events: list[Event] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    events.append(Event(**data))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid event at line {line_number}") from exc
        return events

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> Event:
        event_type = event_type.strip()
        if not event_type:
            raise ValueError("event_type cannot be empty")
        payload = self._bounded_payload(payload or {})
        existing = self._read()
        self.verify()
        sequence = len(existing) + 1
        previous_hash = existing[-1].hash if existing else "0" * 64
        timestamp = time.time()
        digest = hashlib.sha256(self._canonical(sequence, event_type, payload, timestamp, previous_hash)).hexdigest()
        event = Event(sequence, event_type, payload, timestamp, previous_hash, digest)
        encoded = json.dumps(asdict(event), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def events(self) -> list[Event]:
        return self._read()

    def replay(self) -> Iterable[Event]:
        self.verify()
        yield from self._read()

    def verify(self) -> None:
        events = self._read()
        previous = "0" * 64
        for expected_sequence, event in enumerate(events, 1):
            if event.sequence != expected_sequence:
                raise ValueError("event sequence is not contiguous")
            if event.previous_hash != previous:
                raise ValueError(f"broken event chain at sequence {event.sequence}")
            expected_hash = hashlib.sha256(self._canonical(event.sequence, event.event_type,
                                                           event.payload, event.timestamp,
                                                           event.previous_hash)).hexdigest()
            if event.hash != expected_hash:
                raise ValueError(f"event integrity failure at sequence {event.sequence}")
            previous = event.hash

    def snapshot(self) -> dict[str, Any]:
        events = self.events()
        return {"count": len(events), "last_sequence": events[-1].sequence if events else 0,
                "last_hash": events[-1].hash if events else "0" * 64}
