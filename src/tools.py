from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

@dataclass
class ToolRequest:
    action_id: str
    intent: str
    payload: dict
    expected_observation: str
    risk: str = "LOW"

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
    """Provider-neutral tool bus. Adapters are deliberately isolated from planning."""
    def __init__(self):
        self._tools: dict[str, Tool] = {}

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
        return self.resolve(tool_name).execute(request)
