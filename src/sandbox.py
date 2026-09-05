from __future__ import annotations

from dataclasses import dataclass
from .execution import TerminalExecutor, ExecutionResult

@dataclass(frozen=True)
class CommandSpec:
    command: list[str]
    timeout: int = 120
    description: str = ""

class CommandSandbox:
    """Execution boundary used by AUREON before higher-risk host actions."""

    def __init__(self, workspace: str):
        self.executor = TerminalExecutor(workspace)

    def run(self, spec: CommandSpec) -> ExecutionResult:
        return self.executor.run(spec.command, timeout=spec.timeout)
