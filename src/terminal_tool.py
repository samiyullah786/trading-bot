from __future__ import annotations

from .execution import TerminalExecutor
from .tools import ToolRequest, ToolResult


class TerminalTool:
    """ToolRegistry adapter for the terminal execution boundary."""

    name = "terminal"

    def __init__(self, executor: TerminalExecutor):
        self.executor = executor

    def execute(self, request: ToolRequest) -> ToolResult:
        command = request.payload.get("command")
        if not isinstance(command, list) or not command:
            return ToolResult(False, "INVALID_TERMINAL_COMMAND", [])
        try:
            result = self.executor.run(command, request.payload.get("timeout"))
        except Exception as exc:
            return ToolResult(False, f"terminal exception: {type(exc).__name__}: {exc}", [])
        observation = result.stdout.strip()
        if result.stderr.strip():
            observation = (observation + "\n" + result.stderr.strip()).strip()
        if result.truncated:
            observation += "\nOUTPUT_TRUNCATED"
        evidence = [f"terminal.returncode={result.returncode}", f"terminal.duration={result.duration:.6f}"]
        if result.success:
            evidence.append("terminal.command=" + " ".join(result.command))
        return ToolResult(result.success, observation or "command completed", evidence, {
            "returncode": result.returncode,
            "duration": result.duration,
            "truncated": result.truncated,
        })
