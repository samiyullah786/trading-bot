from __future__ import annotations

from dataclasses import dataclass

from .autonomy import AutonomousLoop
from .checkpoint import CheckpointStore
from .ledger import Ledger
from .learning import LearningController, MissionOutcome
from .memory import CognitiveMemory, MemoryItem
from .recovery_engine import EventDrivenRecovery, RecoveryPlan


@dataclass
class AgentRunResult:
    state: str
    cycles: int
    detail: dict


class AgentRuntime:
    """Closed-loop runtime: act, observe, recover, remember, checkpoint."""

    def __init__(self, loop: AutonomousLoop, memory: CognitiveMemory, learning: LearningController, ledger: Ledger | None = None, checkpoints: CheckpointStore | None = None):
        self.loop = loop
        self.memory = memory
        self.learning = learning
        self.ledger = ledger or Ledger()
        self.checkpoints = checkpoints
        self.recovery = EventDrivenRecovery()

    def _checkpoint(self) -> None:
        if self.checkpoints is not None:
            self.checkpoints.save(self.loop.kernel.mission)

    def restore_checkpoint(self, mission_id: str) -> bool:
        if self.checkpoints is None:
            raise RuntimeError("checkpoint store is not configured")
        restored = self.checkpoints.load(mission_id)
        if restored is None:
            return False
        self.loop.kernel.mission = restored
        return True

    def _recover(self, result: dict, mission_id: str, cycle: int) -> RecoveryPlan:
        if result.get("state") not in {"RECOVER", "BLOCKED"}:
            return RecoveryPlan()
        observation = result.get("observation") or result.get("reason") or "unknown failure"
        plan = self.recovery.handle("action.failed", {
            "mission_id": mission_id,
            "action_id": result.get("action", "unknown"),
            "observation": observation,
            "attempt": cycle,
        })
        self.loop.apply_recovery(plan)
        self.ledger.append(
            "recovery.plan",
            f"generated {len(plan.hypotheses)} recovery hypotheses",
            mission_id=mission_id,
            cycle=cycle,
            action_id=result.get("action"),
            observation=observation,
            strategies=[h.strategy for h in plan.hypotheses],
        )
        return plan

    def _record_action_event(self, result: dict, mission_id: str, cycle: int) -> None:
        action_id = result.get("action")
        if not action_id:
            return
        state = result.get("state", "UNKNOWN")
        if state in {"READY", "PROGRESS", "COMPLETE"}:
            self.ledger.append("action.completed", state, mission_id=mission_id, cycle=cycle, action_id=action_id, result=result)
        elif state in {"RECOVER", "BLOCKED"}:
            self.ledger.append("action.failed", state, mission_id=mission_id, cycle=cycle, action_id=action_id, observation=result.get("observation", result.get("reason", "")), result=result)
        else:
            self.ledger.append("action.state", state, mission_id=mission_id, cycle=cycle, action_id=action_id, result=result)

    def run(self, mission_id: str, maximum_cycles: int = 100) -> AgentRunResult:
        if maximum_cycles < 1:
            raise ValueError("maximum_cycles must be positive")
        if self.loop.kernel.mission.id != mission_id:
            raise ValueError("mission_id does not match the active mission")

        for cycle in range(1, maximum_cycles + 1):
            result = self.loop.cycle()
            state = result["state"]
            self.ledger.append("agent_cycle", state, mission_id=mission_id, cycle=cycle)
            self._record_action_event(result, mission_id, cycle)
            recovery = self._recover(result, mission_id, cycle)
            if recovery.hypotheses:
                result["recovery_hypotheses"] = [h.__dict__ for h in recovery.hypotheses]
            self.memory.remember_episode(MemoryItem(
                key=f"{mission_id}:{cycle}", value=result, kind="episode",
                confidence=1.0 if state in ("COMPLETE", "PROGRESS") else 0.5,
                tags={mission_id, state.lower()},
            ))
            self._checkpoint()

            if state == "COMPLETE":
                self.learning.record(MissionOutcome(mission_id, True, "autonomous_loop", "verified mission completion"))
                return AgentRunResult(state, cycle, result)
            if state == "BLOCKED" and not recovery.hypotheses:
                self.learning.record(MissionOutcome(mission_id, False, "autonomous_loop", result.get("reason", "blocked")))
                return AgentRunResult(state, cycle, result)

        return AgentRunResult("PAUSED", maximum_cycles, {"reason": "cycle budget reached"})
