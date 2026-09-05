from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

class Risk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str

class ExecutionPolicy:
    """Explicit safety boundary between planning and real-world mutation."""

    def __init__(self, allow_high_risk: bool = False, allow_critical: bool = False):
        self.allow_high_risk = allow_high_risk
        self.allow_critical = allow_critical

    def evaluate(self, risk: Risk, irreversible: bool = False) -> PolicyDecision:
        if risk == Risk.CRITICAL and not self.allow_critical:
            return PolicyDecision(False, True, "critical action requires explicit approval")
        if risk == Risk.HIGH and not self.allow_high_risk:
            return PolicyDecision(False, True, "high-risk action requires explicit approval")
        if irreversible and risk in (Risk.MEDIUM, Risk.HIGH, Risk.CRITICAL):
            return PolicyDecision(False, True, "irreversible mutation requires approval")
        return PolicyDecision(True, False, "allowed by policy")
