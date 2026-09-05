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

class Tool(Protocol):
    name: str
    def execute(self, request: ToolRequest) -> ToolResult: ...

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> Tool:
        return self._tools[name]
