from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .agent_controller import AgentController, ControllerDecision
from .autonomy import ProposedAction
from .recovery_controller import RecoveryController, RecoveryDecision


@dataclass(frozen=True)
class RecoveryPlan:
    allowed: bool
    recovery: RecoveryDecision
    actions: tuple[ProposedAction, ...] = ()
    reason: str = ""


class RecoveryPlanner:
    """Turn a classified failure into a bounded, validated strategy change."""

    def __init__(
        self,
        controller: AgentController,
        recovery: RecoveryController | None = None,
        *,
        max_actions: int = 32,
        action_validator: Callable[[list[ProposedAction]], str | None] | None = None,
    ) -> None:
        if max_actions < 1:
            raise ValueError("max_actions must be positive")
        self.controller = controller
        self.recovery = recovery or RecoveryController()
        self.max_actions = max_actions
        self.action_validator = action_validator

    def replan(
        self,
        objective: str,
        context: dict,
        failed_action: ProposedAction,
        observation: str,
        failure_class: str = "unknown",
    ) -> RecoveryPlan:
        decision = self.recovery.decide(
            failed_action.action_id or failed_action.description,
            observation,
            failure_class,
        )
        if not decision.allowed:
            return RecoveryPlan(False, decision, reason=decision.reason)

        constraints = [
            "This is recovery, not a blind retry.",
            "Change the strategy materially after the failure.",
            "Do not repeat the failed action command unchanged.",
            "Preserve already verified work and respect action dependencies.",
            f"Previous failed action: {failed_action.description}",
            f"Failure evidence: {observation[:4000]}",
        ]
        planned: ControllerDecision = self.controller.decide(objective, context, constraints)
        actions = list(planned.actions)
        if len(actions) > self.max_actions:
            return RecoveryPlan(False, decision, reason="RECOVERY_PLAN_TOO_LARGE")

        failed_command = tuple(failed_action.command or ())
        if failed_command and any(tuple(action.command or ()) == failed_command for action in actions):
            return RecoveryPlan(False, decision, reason="UNCHANGED_STRATEGY_REJECTED")

        if self.action_validator is not None:
            error = self.action_validator(actions)
            if error is not None:
                return RecoveryPlan(False, decision, reason=f"INVALID_RECOVERY_PLAN:{error}")

        return RecoveryPlan(True, decision, tuple(actions), reason="RECOVERY_PLAN_VALIDATED")
