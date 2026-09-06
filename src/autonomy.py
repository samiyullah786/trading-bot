from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Iterable, Callable

from .domain import Mission, Action, Status
from .kernel import OutcomeKernel
from .recovery import RecoveryEngine
from .critic import AdversarialCritic
from .planner import CandidateAction, Planner


@dataclass
class ProposedAction:
    description: str
    criterion_ids: list[str]
    command: list[str] | None = None
    expected_observation: str = ""
    verification_command: list[str] | None = None
    tool_name: str | None = None
    tool_payload: dict | None = None
    depends_on: list[str] | None = None
    expected_progress: float = 0.5
    success_probability: float = 0.5
    cost: float = 0.0
    risk: float = 0.0
    reversible: bool = True


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
    """Closed outcome loop with candidate planning, execution, verification and replanning."""

    def __init__(
        self,
        kernel: OutcomeKernel,
        strategist: Strategist,
        executor: Callable[[ProposedAction], tuple[bool, str, list[str]]] | None = None,
        critic: AdversarialCritic | None = None,
        planner: Planner | None = None,
    ):
        self.kernel = kernel
        self.strategist = strategist
        self.executor = executor
        self.recovery = RecoveryEngine()
        self.critic = critic or AdversarialCritic()
        self.planner = planner or Planner()
        self.failed_descriptions: set[str] = set()

    def _completion(self) -> tuple[bool, dict]:
        report = self.kernel.report()
        findings = self.critic.inspect(report)
        critical = [f for f in findings if f.severity in {"CRITICAL", "HIGH"}]
        report["critique"] = [f.__dict__ for f in findings]
        return report["complete"] and not critical, report

    def _candidates(self, proposals: list[ProposedAction]) -> list[tuple[CandidateAction, ProposedAction]]:
        pairs: list[tuple[CandidateAction, ProposedAction]] = []
        for proposal in proposals:
            if proposal.description in self.failed_descriptions:
                continue
            candidate = CandidateAction(
                description=proposal.description,
                criterion_ids=list(proposal.criterion_ids),
                expected_progress=proposal.expected_progress,
                success_probability=proposal.success_probability,
                cost=proposal.cost,
                risk=proposal.risk,
                dependencies=set(proposal.depends_on or []),
                reversible=proposal.reversible,
            )
            pairs.append((candidate, proposal))
        return pairs

    def cycle(self) -> dict:
        complete, report = self._completion()
        if complete:
            return {"state": "COMPLETE", "report": report}

        gaps = self.kernel.gaps()
        proposals = list(self.strategist.propose(self.kernel.mission, gaps))
        pairs = self._candidates(proposals)
        if not pairs:
            return {"state": "BLOCKED", "reason": "no viable action proposed", "gaps": gaps, "report": report}

        candidates = [candidate for candidate, _ in pairs]
        completed = {criterion.id for criterion in self.kernel.mission.criteria if criterion.status == Status.VERIFIED}

        # Feasibility is evaluated from the actual current mission state. Alternatives
        # must use the same state; a lack of diverse alternatives is not itself a block.
        plan = self.planner.build_plan(
            candidates,
            completed=completed,
            max_actions=max(1, len(candidates)),
        )
        if not plan.actions:
            return {"state": "BLOCKED", "reason": "no dependency-valid plan", "gaps": gaps, "report": report}

        alternatives = self.planner.diverse_plans(
            candidates,
            count=min(3, len(candidates)),
            max_actions=max(1, len(candidates)),
            completed=completed,
        )
        selected = plan.actions[0]
        proposal = next(proposal for candidate, proposal in pairs if candidate is selected)

        action = Action(
            id=f"A{len(self.kernel.mission.actions) + 1}",
            description=proposal.description,
            criterion_ids=proposal.criterion_ids,
            depends_on=list(proposal.depends_on or []),
            status=Status.READY,
        )
        self.kernel.mission.actions.append(action)
        if self.executor is None:
            return {
                "state": "READY",
                "action": action.id,
                "description": action.description,
                "plan_score": plan.score,
                "plan_size": len(plan.actions),
                "alternative_plans": len(alternatives),
                "gaps": gaps,
                "report": report,
            }

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
            return {
                "state": "COMPLETE" if complete else "PROGRESS",
                "action": action.id,
                "complete": complete,
                "plan_score": plan.score,
                "plan_size": len(plan.actions),
                "alternative_plans": len(alternatives),
                "report": report,
            }

        action.status = Status.FAILED
        self.failed_descriptions.add(proposal.description)
        retry = self.recovery.should_retry(action.id, observation)
        return {
            "state": "RECOVER" if retry else "BLOCKED",
            "action": action.id,
            "observation": observation,
            "retry_allowed": retry,
            "replan_required": True,
            "alternative_plans": len(alternatives),
            "gaps": self.kernel.gaps(),
            "report": self.kernel.report(),
        }

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
