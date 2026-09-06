from __future__ import annotations

from .autonomy import ProposedAction
from .tools import ToolRegistry, ToolRequest


class ToolActionExecutor:
    """Execute actions through explicitly registered tools, never implicit tools."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def __call__(self, action: ProposedAction) -> tuple[bool, str, list[str]]:
        if not action.tool_name:
            return False, "NO_TOOL_SELECTED", []
        request = ToolRequest(
            action_id="runtime-action",
            intent=action.description,
            payload=dict(action.tool_payload or {}),
            expected_observation=action.expected_observation,
        )
        try:
            result = self.registry.execute(action.tool_name, request)
        except Exception as exc:
            return False, f"tool exception: {type(exc).__name__}: {exc}", []
        return result.success, result.observation, list(result.evidence)
