from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Iterable
from .domain import Mission, Action, Status
from .kernel import OutcomeKernel
from .recovery import RecoveryEngine

@dataclass
class ProposedAction:
    description: str
    criterion_ids: list[str]
    command: list[str] | None = None

class Strategist(Protocol):
    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]: ...

class DeterministicStrategist:
    """Fallback strategist for deterministic workflows.

    A real intelligence adapter can replace this without changing the kernel.
    """

    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]:
        for gap in gaps:
            criterion = next(c for c in mission.criteria if c.id == gap)
            yield ProposedAction(
                description=f"Investigate and satisfy: {criterion.statement}",
                criterion_ids=[gap],
            )

class AutonomousLoop:
    """Outcome loop: observe → gap → propose → execute → evidence → verify."""

    def __init__(self, kernel: OutcomeKernel, strategist: Strategist):
        self.kernel = kernel
        self.strategist = strategist
        self.recovery = RecoveryEngine()

    def cycle(self) -> dict:
        if self.kernel.verify():
            return {"state": "COMPLETE", "report": self.kernel.report()}

        gaps = self.kernel.gaps()
        proposals = list(self.strategist.propose(self.kernel.mission, gaps))
        if not proposals:
            return {"state": "BLOCKED", "reason": "no action proposed", "gaps": gaps}

        proposal = proposals[0]
        action = Action(
            id=f"A{len(self.kernel.mission.actions) + 1}",
            description=proposal.description,
            criterion_ids=proposal.criterion_ids,
            status=Status.READY,
        )
        self.kernel.mission.actions.append(action)

        return {
            "state": "READY",
            "action": action.id,
            "description": action.description,
            "gaps": gaps,
        }
