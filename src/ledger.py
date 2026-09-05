from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time
import uuid

@dataclass(frozen=True)
class Evidence:
    criterion_id: str
    statement: str
    source: str
    fingerprint: str
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class ActionRecord:
    action_id: str
    intent: str
    tool: str
    input_fingerprint: str
    outcome: str
    success: bool
    timestamp: float = field(default_factory=time.time)

class EvidenceLedger:
    """Append-only in-memory ledger; persistence is handled by the mission store."""

    def __init__(self):
        self.evidence: list[Evidence] = []
        self.actions: list[ActionRecord] = []

    @staticmethod
    def fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def record_action(self, intent: str, tool: str, payload: str, outcome: str, success: bool) -> ActionRecord:
        record = ActionRecord(str(uuid.uuid4()), intent, tool, self.fingerprint(payload), outcome, success)
        self.actions.append(record)
        return record

    def record_evidence(self, criterion_id: str, statement: str, source: str) -> Evidence:
        item = Evidence(criterion_id, statement, source, self.fingerprint(statement + "|" + source))
        self.evidence.append(item)
        return item
