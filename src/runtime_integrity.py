from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .event_store import EventStore


@dataclass(frozen=True)
class IntegrityReport:
    valid: bool
    event_count: int
    last_sequence: int
    last_hash: str
    error: str | None = None


class RuntimeIntegrity:
    """Fail-closed integrity boundary for durable autonomous state."""

    def __init__(self, store: EventStore):
        self.store = store

    def check(self) -> IntegrityReport:
        try:
            self.store.verify()
            snapshot = self.store.snapshot()
            return IntegrityReport(True, snapshot["count"], snapshot["last_sequence"], snapshot["last_hash"])
        except (OSError, ValueError, TypeError) as exc:
            return IntegrityReport(False, 0, 0, "0" * 64, str(exc))

    def require_valid(self) -> IntegrityReport:
        report = self.check()
        if not report.valid:
            raise RuntimeError(f"runtime integrity check failed: {report.error}")
        return report

    def append_if_valid(self, event_type: str, payload: dict[str, Any] | None = None):
        self.require_valid()
        return self.store.append(event_type, payload)

    def replay_if_valid(self):
        self.require_valid()
        return self.store.replay()
