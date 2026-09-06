from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Iterable, Callable

from .domain import Mission, Action, Status
from .kernel import OutcomeKernel
from .recovery import RecoveryEngine
from .critic import AdversarialCritic


@dataclass
class ProposedAction:
    description: str
    criterion_ids: list[str]
    command: list[str] | None = None
    expected_observation: str = ""
    verification_command: list[str] | None = None


class Strategist(Protocol):
    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]: ...


class DeterministicStrategist:
    def propose(self, mission: Mission, gaps: list[str]) -> Iterable[ProposedAction]:
        for gap in gaps:
            criterion = next(c for c in mission.criteria if c.id == gap)
            yield ProposedAction(
                f"Investigate and satisfy: {criterion.statement}",
                [gap],
                expected_observation=f"evidence that {criterion.statement} is true",
            )


class AutonomousLoop:
    """Closed outcome loop; completion requires verification and a clean adversarial review."""

    def __init__(self, kernel: OutcomeKernel, strategist: Strategist, executor: Callable[[ProposedAction], tuple[bool, str, list[str]]] | None = None, critic: AdversarialCritic | None = None):
        self.kernel = kernel
        self.strategist = strategist
        self.executor = executor
        self.recovery = RecoveryEngine()
        self.critic = critic or AdversarialCritic()

    def _completion(self) -> tuple[bool, dict]:
        report = self.kernel.report()
        findings = self.critic.inspect(report)
        critical = [f for f in findings if f.severity in {"CRITICAL", "HIGH"}]
        report["critique"] = [f.__dict__ for f in findings]
        return report["complete"] and not critical, report

    def cycle(self) -> dict:
        complete, report = self._completion()
        if complete:
            return {"state": "COMPLETE", "report": report}
        gaps = self.kernel.gaps()
        proposals = list(self.strategist.propose(self.kernel.mission, gaps))
        if not proposals:
            return {"state": "BLOCKED", "reason": "no action proposed", "gaps": gaps, "report": report}
        proposal = proposals[0]
        action = Action(id=f"A{len(self.kernel.mission.actions) + 1}", description=proposal.description, criterion_ids=proposal.criterion_ids, status=Status.READY)
        self.kernel.mission.actions.append(action)
        if self.executor is None:
            return {"state": "READY", "action": action.id, "description": action.description, "gaps": gaps, "report": report}
        action.status = Status.RUNNING
        try:
            success, observation, evidence = self.executor(proposal)
        except Exception as exc:
            success, observation, evidence = False, f"executor exception: {type(exc).__name__}: {exc}", []
        action.attempts += 1
        action.result = observation
        self.kernel.observe("executor", observation)
        if success:
            action.status = Status.VERIFIED
            for criterion_id in proposal.criterion_ids:
                for item in evidence:
                    self.kernel.add_evidence(criterion_id, item)
            complete, report = self._completion()
            return {"state": "COMPLETE" if complete else "PROGRESS", "action": action.id, "complete": complete, "report": report}
        action.status = Status.FAILED
        retry = self.recovery.should_retry(action.id, observation)
        return {"state": "RECOVER" if retry else "BLOCKED", "action": action.id, "observation": observation, "retry_allowed": retry, "gaps": self.kernel.gaps(), "report": self.kernel.report()}

    def run(self, maximum_cycles: int = 100) -> dict:
        if maximum_cycles < 1:
            raise ValueError("maximum_cycles must be positive")
        history = []
        for _ in range(maximum_cycles):
            result = self.cycle()
            history.append(result)
            if result["state"] in ("COMPLETE", "BLOCKED"):
                return {"result": result, "history": history}
        return {"result": {"state": "PAUSED", "reason": "cycle budget reached; mission not declared complete", "report": self.kernel.report()}, "history": history}
