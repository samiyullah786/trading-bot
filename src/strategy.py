from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Option:
    name: str
    benefit: float
    probability: float
    cost: float
    risk: float
    reversibility: float

    def utility(self) -> float:
        return self.benefit * self.probability + self.reversibility - self.cost - self.risk

class StrategySelector:
    def select(self, options: list[Option]) -> Option | None:
        return max(options, key=lambda option: option.utility()) if options else None
