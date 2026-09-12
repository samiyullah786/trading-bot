from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .autonomy import ProposedAction
from .mission_scheduler import MissionScheduler
from .recovery_planner import RecoveryPlan, RecoveryPlanner


@dataclass
class RecoveryRecord:
    failed_action_id: str
    failure_class: str
    observation: str
    decision: str
    candidate_action_ids: list[str] = field(default_factory=list)


class RecoveryLifecycle:
    """Authoritative, bounded recovery state for a mission.

    This component never mutates verified work. A recovery plan is accepted only
    after scheduler validation and only when it contains genuinely new action IDs.
    """

    def __init__(self, planner: RecoveryPlanner, *, max_recovery_actions: int = 32) -> None:
        if max_recovery_actions < 1:
            raise ValueError("max_recovery_actions must be positive")
        self.planner = planner
        self.max_recovery_actions = max_recovery_actions
        self.records: list[RecoveryRecord] = []

    def recover(
        self,
        objective: str,
        context: dict,
        actions: Iterable[ProposedAction],
        failed_action: ProposedAction,
        observation: str,
        failure_class: str,
    ) -> RecoveryPlan:
        existing = list(actions)
        existing_ids = {a.action_id for a in existing if a.action_id}
        plan = self.planner.replan(objective, context, failed_action, observation, failure_class)
        if not plan.allowed:
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                plan.reason,
            ))
            return plan

        candidates = list(plan.actions)
        if len(candidates) > self.max_recovery_actions:
            reason = "RECOVERY_ACTION_LIMIT_EXCEEDED"
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                reason,
            ))
            return RecoveryPlan(False, plan.recovery, reason=reason)

        candidate_ids = [a.action_id for a in candidates]
        if any(not action_id for action_id in candidate_ids):
            reason = "RECOVERY_ACTION_ID_REQUIRED"
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                reason,
            ))
            return RecoveryPlan(False, plan.recovery, reason=reason)
        if len(set(candidate_ids)) != len(candidate_ids):
            reason = "RECOVERY_DUPLICATE_ACTION_ID"
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                reason,
            ))
            return RecoveryPlan(False, plan.recovery, reason=reason)
        if existing_ids.intersection(candidate_ids):
            reason = "RECOVERY_ACTION_ID_COLLISION"
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                reason,
            ))
            return RecoveryPlan(False, plan.recovery, reason=reason)

        merged = [self._as_action_dict(a) for a in existing if a.action_id != failed_action.action_id]
        merged.extend(self._as_action_dict(a) for a in candidates)
        try:
            MissionScheduler(merged, max_actions=max(128, len(merged)))
        except ValueError as exc:
            reason = f"INVALID_RECOVERY_GRAPH:{exc}"
            self.records.append(RecoveryRecord(
                failed_action.action_id or failed_action.description,
                plan.recovery.failure_class,
                observation[:4000],
                reason,
                list(candidate_ids),
            ))
            return RecoveryPlan(False, plan.recovery, reason=reason)

        self.records.append(RecoveryRecord(
            failed_action.action_id or failed_action.description,
            plan.recovery.failure_class,
            observation[:4000],
            "RECOVERY_ACCEPTED",
            list(candidate_ids),
        ))
        return plan

    @staticmethod
    def _as_action_dict(action: ProposedAction) -> dict:
        return {
            "action_id": action.action_id,
            "description": action.description,
            "criterion_ids": list(action.criterion_ids),
            "command": list(action.command) if action.command else None,
            "expected_observation": action.expected_observation,
            "verification_command": list(action.verification_command) if action.verification_command else None,
            "tool_name": action.tool_name,
            "tool_payload": dict(action.tool_payload or {}),
            "depends_on": list(action.depends_on),
            "expected_progress": action.expected_progress,
            "success_probability": action.success_probability,
            "cost": action.cost,
            "risk": action.risk,
            "reversible": action.reversible,
        }
