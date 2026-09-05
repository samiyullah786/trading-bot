from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Challenge:
    question: str
    severity: str

class AdversarialCritic:
    """Generates mandatory challenges before a mission may be considered robust."""
    def challenge(self, objective: str, criteria: list[str]) -> list[Challenge]:
        challenges = [
            Challenge(f"What evidence proves the objective is true in the target environment?", "CRITICAL"),
            Challenge("What happens when the primary path fails?", "HIGH"),
            Challenge("What assumptions remain unverified?", "HIGH"),
            Challenge("What input, environment, or dependency could invalidate the result?", "HIGH"),
        ]
        challenges.extend(Challenge(f"Can criterion be falsified: {c}?", "HIGH") for c in criteria)
        return challenges
