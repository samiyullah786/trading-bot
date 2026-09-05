from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time

@dataclass(frozen=True)
class Evidence:
    id: str
    criterion_id: str
    source: str
    observation: str
    timestamp: float
    digest: str

@dataclass
class EvidenceStore:
    items: list[Evidence] = field(default_factory=list)

    def record(self, criterion_id: str, source: str, observation: str) -> Evidence:
        raw = f"{criterion_id}|{source}|{observation}|{time.time_ns()}".encode()
        evidence = Evidence(
            id=hashlib.sha256(raw).hexdigest()[:20],
            criterion_id=criterion_id,
            source=source,
            observation=observation,
            timestamp=time.time(),
            digest=hashlib.sha256(observation.encode()).hexdigest(),
        )
        self.items.append(evidence)
        return evidence

    def for_criterion(self, criterion_id: str) -> list[Evidence]:
        return [x for x in self.items if x.criterion_id == criterion_id]
