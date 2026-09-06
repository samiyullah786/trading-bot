from __future__ import annotations
from dataclasses import dataclass

@dataclass
class QualityGate:
    name: str
    passed: bool
    detail: str

class QualityController:
    """Blocks promotion when mandatory quality gates fail."""
    def evaluate(self, gates: list[QualityGate]) -> tuple[bool, list[QualityGate]]:
        failures = [gate for gate in gates if not gate.passed]
        return not failures, failures
