from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolRequest:
    action_id: str
    intent: str
    payload: dict
    expected_observation: str
    risk: str = "LOW"

    def __post_init__(self) -> None:
        if not self.action_id.strip():
            raise ValueError("action_id must not be empty")
        if not self.intent.strip():
            raise ValueError("intent must not be empty")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")


@dataclass
class ToolResult:
    success: bool
    observation: str
    evidence: list[str]
    metadata: dict | None = None


class Tool(Protocol):
    name: str

    def execute(self, request: ToolRequest) -> ToolResult: ...


class ToolRegistry:
    """Provider-neutral tool bus with optional append-only audit integration."""

    def __init__(self, audit: Any | None = None):
        self._tools: dict[str, Tool] = {}
        self.audit = audit

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, tool_name: str, request: ToolRequest) -> ToolResult:
        if not tool_name.strip():
            raise ValueError("tool_name must not be empty")
        tool = self.resolve(tool_name)
        if self.audit is not None:
            self.audit.append(
                "tool.started",
                f"started tool {tool_name}",
                action_id=request.action_id,
                tool=tool_name,
                intent=request.intent,
                risk=request.risk,
            )
        try:
            result = tool.execute(request)
        except Exception as exc:
            if self.audit is not None:
                self.audit.append(
                    "tool.failed",
                    f"tool {tool_name} raised {type(exc).__name__}",
                    action_id=request.action_id,
                    tool=tool_name,
                    error_type=type(exc).__name__,
                )
            raise
        if self.audit is not None:
            self.audit.append(
                "tool.completed" if result.success else "tool.failed",
                f"tool {tool_name} {'completed' if result.success else 'failed'}",
                action_id=request.action_id,
                tool=tool_name,
                success=result.success,
                observation=result.observation,
                evidence=list(result.evidence),
                metadata=dict(result.metadata or {}),
            )
        return result
