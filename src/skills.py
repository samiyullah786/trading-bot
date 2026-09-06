from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class Skill:
    name: str
    description: str
    preconditions: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0

    @property
    def reliability(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total else 0.0

class SkillLibrary:
    """Reusable procedures learned from mission outcomes."""

    def __init__(self):
        self.skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self.skills[skill.name] = skill

    def record(self, name: str, success: bool) -> None:
        skill = self.skills[name]
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

    def best(self, minimum_reliability: float = 0.0) -> list[Skill]:
        return sorted(
            [s for s in self.skills.values() if s.reliability >= minimum_reliability],
            key=lambda s: s.reliability,
            reverse=True,
        )
