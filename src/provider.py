from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

@dataclass
class ReasoningRequest:
    objective: str
    context: dict
    constraints: list[str]

@dataclass
class ReasoningResponse:
    analysis: str
    actions: list[dict]
    confidence: float
    unknowns: list[str]

class IntelligenceProvider(Protocol):
    """Provider boundary. External intelligence is replaceable, never trusted blindly."""
    def reason(self, request: ReasoningRequest) -> ReasoningResponse: ...

class NullProvider:
    """Safe default: makes no fabricated intelligence claims."""
    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        return ReasoningResponse(
            analysis="No intelligence provider configured.",
            actions=[],
            confidence=0.0,
            unknowns=["reasoning provider"],
        )
