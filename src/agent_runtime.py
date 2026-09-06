from __future__ import annotations

from dataclasses import dataclass
from .autonomy import AutonomousLoop
from .ledger import Ledger
from .memory import CognitiveMemory, MemoryItem
from .learning import LearningController, MissionOutcome

@dataclass
class AgentRunResult:
    state: str
    cycles: int
    detail: dict

class AgentRuntime:
    """Closed-loop agent runtime: act, observe, remember, learn."""

    def __init__(self, loop: AutonomousLoop, memory: CognitiveMemory, learning: LearningController, ledger: Ledger | None = None):
        self.loop = loop
        self.memory = memory
        self.learning = learning
        self.ledger = ledger or Ledger()

    def run(self, mission_id: str, maximum_cycles: int = 100) -> AgentRunResult:
        for cycle in range(1, maximum_cycles + 1):
            result = self.loop.cycle()
            state = result["state"]
            self.ledger.append("agent_cycle", state, mission_id=mission_id, cycle=cycle)
            self.memory.remember_episode(MemoryItem(
                key=f"{mission_id}:{cycle}",
                value=result,
                kind="episode",
                confidence=1.0 if state in ("COMPLETE", "PROGRESS") else 0.5,
                tags={mission_id, state.lower()},
            ))

            if state == "COMPLETE":
                self.learning.record(MissionOutcome(mission_id, True, "autonomous_loop", "verified mission completion"))
                return AgentRunResult(state, cycle, result)
            if state == "BLOCKED":
                self.learning.record(MissionOutcome(mission_id, False, "autonomous_loop", result.get("reason", "blocked")))
                return AgentRunResult(state, cycle, result)

        return AgentRunResult("PAUSED", maximum_cycles, {"reason": "cycle budget reached"})
