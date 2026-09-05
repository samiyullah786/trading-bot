from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class CandidateAction:
    description: str
    criterion_ids: list[str]
    expected_progress: float
    success_probability: float
    cost: float
    risk: float
    dependencies: set[str] = field(default_factory=set)
    reversible: bool = True

    @property
    def score(self) -> float:
        benefit = max(0.0, min(1.0, self.expected_progress)) * max(0.0, min(1.0, self.success_probability))
        penalty = max(0.0, self.cost) + max(0.0, self.risk)
        if not self.reversible:
            penalty += 1.0
        return benefit - penalty

class Planner:
    """Explicit candidate ranking with dependency and safety checks."""

    def rank(self, candidates: list[CandidateAction]) -> list[CandidateAction]:
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def choose(self, candidates: list[CandidateAction]) -> CandidateAction | None:
        return self.rank(candidates)[0] if candidates else None

    def choose_safe(self, candidates: list[CandidateAction], max_risk: float) -> CandidateAction | None:
        safe = [candidate for candidate in candidates if candidate.risk <= max_risk]
        return self.choose(safe)

    def is_materially_better(self, current: CandidateAction, alternative: CandidateAction, switching_cost: float = 0.0) -> bool:
        return alternative.score > current.score + max(0.0, switching_cost)
