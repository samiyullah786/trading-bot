from __future__ import annotations

from dataclasses import dataclass
from .agent_controller import AgentController
from .autonomy import AutonomousLoop, ProposedAction
from .domain import Mission
from .kernel import OutcomeKernel
from .action_executor import ActionExecutor

class ControllerStrategist:
    """Adapts an AgentController to the autonomous execution loop."""

    def __init__(self, controller: AgentController, constraints: list[str] | None = None):
        self.controller = controller
        self.constraints = constraints or []

    def propose(self, mission: Mission, gaps: list[str]):
        context = {
            "objective": mission.objective,
            "gaps": gaps,
            "criteria": [{"id": c.id, "statement": c.statement} for c in mission.criteria],
        }
        decision = self.controller.decide(mission.objective, context, mission.constraints + self.constraints)
        for action in decision.actions:
            yield action

@dataclass
class MissionExecution:
    mission_id: str
    state: str
    history: list[dict]
    report: dict

class EndToEndMissionExecutor:
    """Runs provider → plan → terminal → evidence → verification."""

    def __init__(self, controller: AgentController, executor: ActionExecutor):
        self.controller = controller
        self.executor = executor

    def execute(self, mission: Mission, maximum_cycles: int = 100) -> MissionExecution:
        kernel = OutcomeKernel(mission)
        strategist = ControllerStrategist(self.controller)
        loop = AutonomousLoop(kernel, strategist, self.executor)
        result = loop.run(maximum_cycles)
        final = result["result"]
        report = final.get("report", kernel.report())
        return MissionExecution(
            mission.id,
            final["state"],
            result["history"],
            report,
        )
