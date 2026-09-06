from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import tempfile
import time
from typing import Any, Iterable


@dataclass(frozen=True)
class Event:
    sequence: int
    event_type: str
    payload: dict[str, Any]
    timestamp: float
    previous_hash: str
    hash: str


class EventStore:
    """Durable append-only event log with a tamper-evident hash chain.

    The store is deliberately dependency-free. Each event is one JSON object
    per line, written with flush+fsync before the append is acknowledged.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _canonical(sequence: int, event_type: str, payload: dict[str, Any], timestamp: float, previous_hash: str) -> bytes:
        return json.dumps(
            {
                "sequence": sequence,
                "event_type": event_type,
                "payload": payload,
                "timestamp": timestamp,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

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
        payload = dict(payload or {})
        existing = self._read()
        sequence = len(existing) + 1
        previous_hash = existing[-1].hash if existing else "0" * 64
        timestamp = time.time()
        digest = hashlib.sha256(
            self._canonical(sequence, event_type, payload, timestamp, previous_hash)
        ).hexdigest()
        event = Event(sequence, event_type, payload, timestamp, previous_hash, digest)
        encoded = json.dumps(asdict(event), sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def events(self) -> list[Event]:
        return self._read()

    def replay(self) -> Iterable[Event]:
        yield from self._read()

    def verify(self) -> None:
        events = self._read()
        previous = "0" * 64
        for expected_sequence, event in enumerate(events, 1):
            if event.sequence != expected_sequence:
                raise ValueError("event sequence is not contiguous")
            if event.previous_hash != previous:
                raise ValueError(f"broken event chain at sequence {event.sequence}")
            expected_hash = hashlib.sha256(
                self._canonical(
                    event.sequence,
                    event.event_type,
                    event.payload,
                    event.timestamp,
                    event.previous_hash,
                )
            ).hexdigest()
            if event.hash != expected_hash:
                raise ValueError(f"event integrity failure at sequence {event.sequence}")
            previous = event.hash

    def snapshot(self) -> dict[str, Any]:
        events = self.events()
        return {
            "count": len(events),
            "last_sequence": events[-1].sequence if events else 0,
            "last_hash": events[-1].hash if events else "0" * 64,
        }
