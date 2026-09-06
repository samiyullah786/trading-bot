from __future__ import annotations

from dataclasses import dataclass

@dataclass
class TransferCase:
    source_domain: str
    target_domain: str
    source_score: float
    target_score: float

class TransferEvaluator:
    """Measures whether performance transfers beyond the training context."""

    def evaluate(self, case: TransferCase) -> float:
        if case.source_score <= 0:
            return 0.0
        return max(0.0, min(1.0, case.target_score / case.source_score))

    def is_generalizable(self, case: TransferCase, threshold: float = 0.7) -> bool:
        return self.evaluate(case) >= threshold
