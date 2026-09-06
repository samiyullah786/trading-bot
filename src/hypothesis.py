from __future__ import annotations

from dataclasses import dataclass, field
import uuid

@dataclass
class Hypothesis:
    statement: str
    confidence: float
    assumptions: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Experiment:
    hypothesis_id: str
    action: str
    expected_support: str
    expected_refutation: str

class HypothesisEngine:
    """Tracks competing explanations instead of committing to one guess."""

    def rank(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        return sorted(hypotheses, key=lambda h: h.confidence, reverse=True)

    def update(self, hypothesis: Hypothesis, supported: bool, strength: float = 0.1) -> Hypothesis:
        delta = abs(strength) if supported else -abs(strength)
        hypothesis.confidence = max(0.0, min(1.0, hypothesis.confidence + delta))
        return hypothesis

    def select_experiment(self, hypothesis: Hypothesis, action: str) -> Experiment:
        return Experiment(
            hypothesis_id=hypothesis.id,
            action=action,
            expected_support=f"observation supporting: {hypothesis.statement}",
            expected_refutation=f"observation contradicting: {hypothesis.statement}",
        )
