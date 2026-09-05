from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False

class Policy:
    """Explicit action boundary. High-impact operations require approval."""
    HIGH_RISK = {"delete", "credential", "financial", "production-destructive", "system-wide"}

    def evaluate(self, intent: str, risk: str = "LOW") -> PolicyDecision:
        text = f"{intent} {risk}".lower()
        if any(word in text for word in self.HIGH_RISK):
            return PolicyDecision(False, "high-impact action requires explicit approval", True)
        return PolicyDecision(True, "allowed by policy")
