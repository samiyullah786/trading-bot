from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from .execution import TerminalExecutor, ExecutionResult

@dataclass(frozen=True)
class ShellCommand:
    argv: list[str]
    shell: str = "native"

class CommandRouter:
    """Cross-platform command boundary without invoking a shell by default."""
    def __init__(self, executor: TerminalExecutor):
        self.executor = executor

    def run(self, command: ShellCommand) -> ExecutionResult:
        if not command.argv or not all(isinstance(x, str) and x for x in command.argv):
            raise ValueError("command argv must contain non-empty strings")
        shell = command.shell.lower()
        if shell == "native":
            return self.executor.run(command.argv)
        if shell == "bash":
            program = shutil.which("bash")
            if not program: raise RuntimeError("bash is unavailable")
            return self.executor.run([program, "-lc", " ".join(_quote(x) for x in command.argv)])
        if shell == "powershell":
            program = shutil.which("pwsh") or shutil.which("powershell")
            if not program: raise RuntimeError("PowerShell is unavailable")
            return self.executor.run([program, "-NoProfile", "-Command", "& " + " ".join(_quote(x) for x in command.argv)])
        if shell == "cmd":
            if platform.system().lower() != "windows": raise RuntimeError("cmd is unavailable on this platform")
            return self.executor.run([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", " ".join(_quote(x) for x in command.argv)])
        raise ValueError(f"unsupported shell: {command.shell}")

def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
