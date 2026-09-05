from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

@dataclass
class IntelligenceRequest:
    objective: str
    world_state: dict
    instruction: str

@dataclass
class IntelligenceResponse:
    text: str
    structured: dict

class IntelligenceProvider(Protocol):
    """Provider boundary.

    The AUREON control system is custom. This interface allows an external
    reasoning model to be connected without importing an agent framework.
    """

    def think(self, request: IntelligenceRequest) -> IntelligenceResponse: ...
