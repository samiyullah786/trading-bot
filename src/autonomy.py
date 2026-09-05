from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Iterable, Callable
from .domain import Mission, Action, Status
from .kernel import OutcomeKernel
from .recovery import RecoveryEngine

@dataclass
class ProposedAction:
    description: str
    criterion_ids: list[str]
    command: list[str] | None = None
    expected_observation: str = ""

class Strategist(Protocol):
    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]: ...

class DeterministicStrategist:
    """Fallback strategist for deterministic workflows."""

    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]:
        for gap in gaps:
            criterion = next(c for c in mission.criteria if c.id == gap)
            yield ProposedAction(
                description=f"Investigate and satisfy: {criterion.statement}",
                criterion_ids=[gap],
                expected_observation=f"evidence that {criterion.statement} is true",
            )

class AutonomousLoop:
    """Outcome loop with bounded execution and evidence accounting."""

    def __init__(
        self,
        kernel: OutcomeKernel,
        strategist: Strategist,
        executor: Callable[[ProposedAction], tuple[bool, str, list[str]]] | None = None,
    ):
        self.kernel = kernel
        self.strategist = strategist
        self.executor = executor
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

        if self.executor is None:
            return {
                "state": "READY",
                "action": action.id,
                "description": action.description,
                "gaps": gaps,
            }

        action.status = Status.RUNNING
        success, observation, evidence = self.executor(proposal)
        action.attempts += 1
        action.result = observation
        self.kernel.observe("executor", observation)

        if success:
            action.status = Status.VERIFIED
            for criterion_id in proposal.criterion_ids:
                for item in evidence:
                    self.kernel.add_evidence(criterion_id, item)
            return {
                "state": "PROGRESS",
                "action": action.id,
                "complete": self.kernel.verify(),
                "report": self.kernel.report(),
            }

        action.status = Status.FAILED
        retry = self.recovery.should_retry(action.id, observation)
        return {
            "state": "RECOVER" if retry else "BLOCKED",
            "action": action.id,
            "observation": observation,
            "retry_allowed": retry,
            "gaps": self.kernel.gaps(),
        }

    def run(self, maximum_cycles: int = 100) -> dict:
        """Runs until completion, a blocker, or an explicit cycle budget.

        The budget is a safety boundary, not a definition of completion.
        """
        history = []
        for _ in range(maximum_cycles):
            result = self.cycle()
            history.append(result)
            if result["state"] in ("COMPLETE", "BLOCKED"):
                return {"result": result, "history": history}
        return {
            "result": {
                "state": "PAUSED",
                "reason": "cycle budget reached; mission not declared complete",
                "report": self.kernel.report(),
            },
            "history": history,
        }
