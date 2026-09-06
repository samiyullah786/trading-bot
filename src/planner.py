from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations


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


@dataclass
class Plan:
    """An ordered, internally consistent candidate strategy."""

    actions: list[CandidateAction]
    score: float


class Planner:
    """Rank and compose candidate actions without hiding safety decisions."""

    def rank(self, candidates: list[CandidateAction]) -> list[CandidateAction]:
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def choose(self, candidates: list[CandidateAction]) -> CandidateAction | None:
        return self.rank(candidates)[0] if candidates else None

    def choose_safe(self, candidates: list[CandidateAction], max_risk: float) -> CandidateAction | None:
        safe = [candidate for candidate in candidates if candidate.risk <= max_risk]
        return self.choose(safe)

    def feasible(self, candidate: CandidateAction, completed: set[str]) -> bool:
        return candidate.dependencies.issubset(completed)

    def is_materially_better(
        self,
        current: CandidateAction,
        alternative: CandidateAction,
        switching_cost: float = 0.0,
    ) -> bool:
        return alternative.score > current.score + max(0.0, switching_cost)

    def build_plan(
        self,
        candidates: list[CandidateAction],
        completed: set[str] | None = None,
        max_actions: int = 8,
        max_risk: float = 1.0,
    ) -> Plan:
        """Greedily construct a dependency-valid plan, reconsidering readiness.

        This is deliberately deterministic and explainable. It is a planning
        primitive, not a claim that a single heuristic is globally optimal.
        """
        if max_actions < 1:
            raise ValueError("max_actions must be positive")
        completed = set(completed or set())
        remaining = list(candidates)
        chosen: list[CandidateAction] = []

        while remaining and len(chosen) < max_actions:
            ready = [
                c for c in remaining
                if c.risk <= max_risk and self.feasible(c, completed)
            ]
            if not ready:
                break
            selected = self.choose(ready)
            if selected is None:
                break
            chosen.append(selected)
            remaining.remove(selected)
            completed.update(selected.criterion_ids)

        return Plan(chosen, sum(action.score for action in chosen))

    def diverse_plans(
        self,
        candidates: list[CandidateAction],
        count: int = 3,
        max_actions: int = 8,
    ) -> list[Plan]:
        """Return distinct high-scoring alternatives for deliberate replanning."""
        if count < 1:
            raise ValueError("count must be positive")
        ranked = self.rank(candidates)
        if not ranked:
            return []
        plans: list[Plan] = []
        seeds = ranked[: min(len(ranked), count)]
        for seed in seeds:
            rest = [candidate for candidate in ranked if candidate is not seed]
            plan = self.build_plan([seed, *rest], max_actions=max_actions)
            if plan.actions:
                plans.append(plan)
        unique: list[Plan] = []
        signatures: set[tuple[str, ...]] = set()
        for plan in sorted(plans, key=lambda p: p.score, reverse=True):
            signature = tuple(action.description for action in plan.actions)
            if signature not in signatures:
                signatures.add(signature)
                unique.append(plan)
        return unique[:count]
