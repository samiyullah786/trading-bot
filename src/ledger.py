from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from .event_store import EventStore


@dataclass
class LedgerEntry:
    sequence: int
    kind: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Ledger:
    """Append-only mission history with optional durable event backing."""

    def __init__(self, event_store: EventStore | None = None):
        self.entries: list[LedgerEntry] = []
        self.event_store = event_store

    def append(self, kind: str, message: str, **data) -> LedgerEntry:
        entry = LedgerEntry(len(self.entries) + 1, kind, message, data)
        self.entries.append(entry)
        if self.event_store is not None:
            self.event_store.append(
                "ledger.entry",
                {
                    "sequence": entry.sequence,
                    "kind": kind,
                    "message": message,
                    "data": data,
                    "timestamp": entry.timestamp,
                },
            )
        return entry

    def recent(self, count: int = 20) -> list[LedgerEntry]:
        if count < 0:
            raise ValueError("count must be non-negative")
        return self.entries[-count:] if count else []
