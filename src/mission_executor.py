from __future__ import annotations
from dataclasses import dataclass
from .agent_controller import AgentController
from .autonomy import AutonomousLoop
from .domain import Mission
from .kernel import OutcomeKernel
from .action_executor import ActionExecutor

class ControllerStrategist:
    def __init__(self, controller: AgentController, constraints: list[str] | None = None):
        self.controller = controller
        self.constraints = constraints or []

    def propose(self, mission: Mission, gaps: list[str]):
        context = {"objective": mission.objective, "gaps": gaps, "criteria": [{"id": c.id, "statement": c.statement} for c in mission.criteria]}
        decision = self.controller.decide(mission.objective, context, mission.constraints + self.constraints)
        yield from decision.actions

@dataclass
class MissionExecution:
    mission_id: str
    state: str
    history: list[dict]
    report: dict

class EndToEndMissionExecutor:
    def __init__(self, controller: AgentController, executor: ActionExecutor):
        self.controller = controller
        self.executor = executor

    def execute(self, mission: Mission, maximum_cycles: int = 100) -> MissionExecution:
        kernel = OutcomeKernel(mission)
        loop = AutonomousLoop(kernel, ControllerStrategist(self.controller), self.executor)
        result = loop.run(maximum_cycles)
        final = result["result"]
        return MissionExecution(mission.id, final["state"], result["history"], final.get("report", kernel.report()))
