from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time

from .security import EnvironmentFilter, SecurityProfile, SecretRedactor


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    duration: float
    command: list[str]
    truncated: bool = False


class TerminalExecutor:
    """Standard-library execution boundary with bounded output and env hygiene."""

    name = "terminal"

    def __init__(
        self,
        workspace: str | Path,
        timeout: int = 120,
        profile: SecurityProfile | None = None,
        secrets: list[str] | None = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.profile = profile or SecurityProfile(timeout_seconds=float(timeout))
        self.env_filter = EnvironmentFilter(self.profile)
        self.redactor = SecretRedactor()
        self.secrets = list(secrets or [])
        if self.profile.timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        if self.profile.max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")

    def _bound(self, value: str) -> tuple[str, bool]:
        encoded = value.encode("utf-8", errors="replace")
        if len(encoded) <= self.profile.max_output_bytes:
            return self.redactor.redact(value, self.secrets), False
        clipped = encoded[: self.profile.max_output_bytes].decode("utf-8", errors="ignore")
        return self.redactor.redact(clipped, self.secrets), True

    def run(self, command: list[str], timeout: int | float | None = None) -> ExecutionResult:
        if not command:
            raise ValueError("command cannot be empty")
        if any(not isinstance(part, str) or not part for part in command):
            raise ValueError("command arguments must be non-empty strings")

        started = time.monotonic()
        effective_timeout = float(timeout) if timeout is not None else self.profile.timeout_seconds
        if effective_timeout <= 0:
            raise ValueError("timeout must be positive")
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                shell=False,
                env=self.env_filter.build(),
            )
            stdout, out_truncated = self._bound(completed.stdout or "")
            stderr, err_truncated = self._bound(completed.stderr or "")
            return ExecutionResult(
                success=completed.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                returncode=completed.returncode,
                duration=time.monotonic() - started,
                command=list(command),
                truncated=out_truncated or err_truncated,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            stdout, out_truncated = self._bound(stdout if isinstance(stdout, str) else "")
            stderr, err_truncated = self._bound(stderr if isinstance(stderr, str) else "")
            return ExecutionResult(
                success=False,
                stdout=stdout,
                stderr=(stderr + "\nTIMEOUT").strip(),
                returncode=-1,
                duration=time.monotonic() - started,
                command=list(command),
                truncated=out_truncated or err_truncated,
            )
