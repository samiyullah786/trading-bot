from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

@dataclass
class Evidence:
    source: str
    claim: str
    content: str

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.claim}|{self.content}".encode()
        return hashlib.sha256(raw).hexdigest()[:20]

class EvidenceStore:
    """Deduplicated evidence collection independent of any model provider."""

    def __init__(self):
        self._items: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> str:
        self._items[evidence.fingerprint] = evidence
        return evidence.fingerprint

    def find(self, claim: str) -> list[Evidence]:
        needle = claim.lower()
        return [item for item in self._items.values() if needle in item.claim.lower()]

    def all(self) -> list[Evidence]:
        return list(self._items.values())
