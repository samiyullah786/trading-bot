from __future__ import annotations
from .domain import Mission, Criterion

class MissionFactory:
    """Converts structured requirements into explicit mission contracts."""

    def create(self, objective: str, requirements: list[str]) -> Mission:
        if not objective.strip():
            raise ValueError("objective required")
        criteria = [
            Criterion(f"R{i + 1}", requirement)
            for i, requirement in enumerate(requirements)
            if requirement.strip()
        ]
        if not criteria:
            raise ValueError("at least one requirement required")
        return Mission.create(objective, criteria)
