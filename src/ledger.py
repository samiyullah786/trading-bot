from __future__ import annotations
from dataclasses import dataclass, field
import time

@dataclass
class LedgerEntry:
    sequence: int
    kind: str
    message: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class Ledger:
    """Append-only mission history for debugging and recovery."""
    def __init__(self):
        self.entries: list[LedgerEntry] = []

    def append(self, kind: str, message: str, **data) -> LedgerEntry:
        entry = LedgerEntry(len(self.entries) + 1, kind, message, data)
        self.entries.append(entry)
        return entry

    def recent(self, count: int = 20) -> list[LedgerEntry]:
        return self.entries[-count:]
