from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class BrowserRequest:
    action_id: str
    operation: str
    target: str = ""
    value: str = ""
    expected: str = ""

@dataclass(frozen=True)
class BrowserResult:
    success: bool
    observation: str
    evidence: list[str]
    url: str = ""

class BrowserAdapter(Protocol):
    """AUREON-owned browser contract; concrete browser transport is replaceable."""
    name: str
    def execute(self, request: BrowserRequest) -> BrowserResult: ...
