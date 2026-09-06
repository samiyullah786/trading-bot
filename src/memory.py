from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time

@dataclass
class MemoryItem:
    key: str
    value: Any
    kind: str = "fact"
    confidence: float = 1.0
    tags: set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    accesses: int = 0

class CognitiveMemory:
    """Custom multi-store memory for missions and reusable knowledge."""

    def __init__(self):
        self.working: dict[str, MemoryItem] = {}
        self.episodic: list[MemoryItem] = []
        self.semantic: dict[str, MemoryItem] = {}

    def remember_working(self, item: MemoryItem) -> None:
        self.working[item.key] = item

    def remember_episode(self, item: MemoryItem) -> None:
        self.episodic.append(item)

    def remember_knowledge(self, item: MemoryItem) -> None:
        self.semantic[item.key] = item

    def recall(self, query: str) -> list[MemoryItem]:
        needle = query.lower()
        candidates = list(self.working.values()) + self.episodic + list(self.semantic.values())
        found = []
        for item in candidates:
            haystack = f"{item.key} {item.value} {' '.join(item.tags)}".lower()
            if needle in haystack:
                item.accesses += 1
                found.append(item)
        return found

    def context(self) -> dict:
        return {
            "working": {k: v.value for k, v in self.working.items()},
            "episodes": len(self.episodic),
            "knowledge": len(self.semantic),
        }
