from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import json
import time

@dataclass(frozen=True)
class Event:
    kind: str
    mission_id: str
    payload: dict[str, Any]
    timestamp: float

class EventLog:
    """Append-only mission event log for auditability and crash recovery."""
    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, kind: str, mission_id: str, payload: dict[str, Any]) -> Event:
        event = Event(kind, mission_id, payload, time.time())
        self.events.append(event)
        return event

    def export(self) -> str:
        return json.dumps([asdict(e) for e in self.events], indent=2)
