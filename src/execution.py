from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import time

@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    duration: float
    command: list[str]

class TerminalExecutor:
    """Custom terminal execution adapter using only the Python standard library."""

    name = "terminal"

    def __init__(self, workspace: str | Path, timeout: int = 120):
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout

    def run(self, command: list[str], timeout: int | None = None) -> ExecutionResult:
        if not command:
            raise ValueError("command cannot be empty")

        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                shell=False,
                env=os.environ.copy(),
            )
            return ExecutionResult(
                success=completed.returncode == 0,
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
                duration=time.monotonic() - started,
                command=command,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                success=False,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr="TIMEOUT",
                returncode=-1,
                duration=time.monotonic() - started,
                command=command,
            )
