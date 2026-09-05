from __future__ import annotations

from dataclasses import dataclass
from .domain import Mission

@dataclass
class CandidateAction:
    description: str
    criterion_ids: list[str]
    expected_progress: float
    success_probability: float
    cost: float
    risk: float
    reversible: bool = True

    @property
    def score(self) -> float:
        benefit = self.expected_progress * self.success_probability
        penalty = self.cost + self.risk + (0.0 if self.reversible else 1.0)
        return benefit - penalty

class Planner:
    """Deterministic selection layer for candidate actions.

    A reasoning provider can generate candidates; AUREON evaluates and orders
    them using explicit state rather than opaque completion claims.
    """

    def rank(self, candidates: list[CandidateAction]) -> list[CandidateAction]:
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def choose(self, candidates: list[CandidateAction]) -> CandidateAction | None:
        ranked = self.rank(candidates)
        return ranked[0] if ranked else None
