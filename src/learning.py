from __future__ import annotations

from dataclasses import dataclass
from .skills import SkillLibrary

@dataclass
class MissionOutcome:
    mission_id: str
    success: bool
    strategy: str
    lesson: str

class LearningController:
    """Converts verified outcomes into reusable, inspectable learning signals."""

    def __init__(self, skills: SkillLibrary):
        self.skills = skills
        self.outcomes: list[MissionOutcome] = []

    def record(self, outcome: MissionOutcome) -> None:
        self.outcomes.append(outcome)
        if outcome.strategy in self.skills.skills:
            self.skills.record(outcome.strategy, outcome.success)

    def lessons(self) -> list[str]:
        return [outcome.lesson for outcome in self.outcomes if outcome.lesson]
