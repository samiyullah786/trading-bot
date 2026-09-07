from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
import time
from typing import Any

_SECRET_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)",
    re.I,
)
_SECRET_VALUE = re.compile(r"(?i)\b(?:bearer\s+)?[A-Za-z0-9_\-]{24,}\b")
_MAX_OBSERVATION = 4096
_MAX_SOURCE = 512
_MAX_CRITERION = 256
_MAX_ITEMS = 100_000


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

    @staticmethod
    def _clean(value: str, limit: int) -> str:
        value = str(value)[:limit]
        return _SECRET_VALUE.sub("[REDACTED]", value)

    @classmethod
    def _clean_keyed(cls, value: Any, key: str | None = None) -> Any:
        if key and _SECRET_KEY.search(key):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(k): cls._clean_keyed(v, str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._clean_keyed(v) for v in value]
        if isinstance(value, str):
            return cls._clean(value, _MAX_OBSERVATION)
        return str(value)[:_MAX_OBSERVATION]

    def record(self, criterion_id: str, source: str, observation: str) -> Evidence:
        if len(self.items) >= _MAX_ITEMS:
            raise ValueError("evidence store exceeds safety item limit")
        criterion = self._clean(criterion_id, _MAX_CRITERION)
        clean_source = self._clean(source, _MAX_SOURCE)
        clean_observation = self._clean(str(observation), _MAX_OBSERVATION)
        raw = f"{criterion}|{clean_source}|{clean_observation}|{time.time_ns()}".encode()
        evidence = Evidence(
            id=hashlib.sha256(raw).hexdigest()[:20],
            criterion_id=criterion,
            source=clean_source,
            observation=clean_observation,
            timestamp=time.time(),
            digest=hashlib.sha256(clean_observation.encode()).hexdigest(),
        )
        self.items.append(evidence)
        return evidence

    def for_criterion(self, criterion_id: str) -> list[Evidence]:
        return [x for x in self.items if x.criterion_id == criterion_id]
