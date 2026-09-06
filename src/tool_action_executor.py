from __future__ import annotations

from .autonomy import ProposedAction
from .policy import ExecutionPolicy, Risk
from .tools import ToolRegistry, ToolRequest


class ToolActionExecutor:
    """Execute planned actions through registered tools and an explicit policy boundary."""

    def __init__(self, registry: ToolRegistry, policy: ExecutionPolicy | None = None):
        self.registry = registry
        self.policy = policy or ExecutionPolicy()

    @staticmethod
    def _risk(value: str | float | None) -> Risk:
        if isinstance(value, str):
            try:
                return Risk[value.upper()]
            except KeyError:
                pass
        if isinstance(value, (int, float)):
            if value >= 0.75:
                return Risk.CRITICAL
            if value >= 0.5:
                return Risk.HIGH
            if value >= 0.25:
                return Risk.MEDIUM
        return Risk.LOW

    def __call__(self, action: ProposedAction) -> tuple[bool, str, list[str]]:
        if not action.tool_name:
            return False, "NO_TOOL_SELECTED", []
        risk = self._risk(action.risk)
        decision = self.policy.evaluate(risk, irreversible=not action.reversible)
        if not decision.allowed:
            return False, "POLICY_BLOCKED: " + decision.reason, []
        action_id = getattr(action, "action_id", None) or "runtime-action"
        request = ToolRequest(
            action_id=action_id,
            intent=action.description,
            payload=dict(action.tool_payload or {}),
            expected_observation=action.expected_observation,
            risk=risk.value,
        )
        try:
            result = self.registry.execute(action.tool_name, request)
        except Exception as exc:
            return False, f"tool exception: {type(exc).__name__}: {exc}", []
        return result.success, result.observation, list(result.evidence)
