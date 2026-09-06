from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class ToolCall:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolOutcome:
    success: bool
    observation: str
    evidence: list[str] = field(default_factory=list)

class ToolRouter:
    """Single explicit dispatch point for AUREON capabilities."""
    def __init__(self):
        self._handlers: dict[str, Callable[[dict], ToolOutcome]] = {}

    def register(self, name: str, handler: Callable[[dict], ToolOutcome]) -> None:
        if name in self._handlers:
            raise ValueError(f"tool already registered: {name}")
        self._handlers[name] = handler

    def execute(self, call: ToolCall) -> ToolOutcome:
        if call.name not in self._handlers:
            return ToolOutcome(False, f"UNKNOWN_TOOL:{call.name}")
        return self._handlers[call.name](call.payload)

    def names(self) -> list[str]:
        return sorted(self._handlers)
