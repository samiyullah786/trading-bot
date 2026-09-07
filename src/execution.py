from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import time

from .security import EnvironmentFilter, ExecutablePolicy, SecurityProfile, SecretRedactor


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    duration: float
    command: list[str]
    truncated: bool = False
    timed_out: bool = False


class TerminalExecutor:
    """Fail-closed subprocess boundary with strict workspace and process limits."""

    name = "terminal"

    def __init__(self, workspace: str | Path, timeout: int = 120,
                 profile: SecurityProfile | None = None, secrets: list[str] | None = None):
        self.workspace = Path(workspace).resolve()
        if not self.workspace.exists() or not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        self.profile = profile or SecurityProfile(timeout_seconds=float(timeout))
        self.env_filter = EnvironmentFilter(self.profile)
        self.executable_policy = ExecutablePolicy(self.profile)
        self.redactor = SecretRedactor()
        self.secrets = list(secrets or [])
        if self.profile.timeout_seconds <= 0 or self.profile.max_output_bytes < 1:
            raise ValueError("invalid execution limits")

    def _bound(self, value: str | bytes | None) -> tuple[str, bool]:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        encoded = (value or "").encode("utf-8", errors="replace")
        truncated = len(encoded) > self.profile.max_output_bytes
        if truncated:
            encoded = encoded[:self.profile.max_output_bytes]
        clean = encoded.decode("utf-8", errors="ignore")
        return self.redactor.redact(clean, self.secrets), truncated

    def _preexec(self):
        if os.name != "posix":
            return None
        import resource
        file_limit = max(self.profile.max_output_bytes * 4, 1_000_000)
        def apply_limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return apply_limits

    def run(self, command: list[str], timeout: int | float | None = None) -> ExecutionResult:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("command arguments must be non-empty strings")
        self.executable_policy.validate(command[0])
        started = time.monotonic()
        effective_timeout = float(timeout) if timeout is not None else self.profile.timeout_seconds
        if effective_timeout <= 0:
            raise ValueError("timeout must be positive")
        if shutil.which(command[0]) is None and not Path(command[0]).is_absolute():
            return ExecutionResult(False, "", f"executable not found: {command[0]}", 127,
                                   time.monotonic() - started, list(command))
        try:
            completed = subprocess.run(
                command, cwd=self.workspace, capture_output=True, text=False,
                timeout=effective_timeout, shell=False, env=self.env_filter.build(),
                preexec_fn=self._preexec(),
            )
            stdout, out_truncated = self._bound(completed.stdout)
            stderr, err_truncated = self._bound(completed.stderr)
            return ExecutionResult(completed.returncode == 0, stdout, stderr,
                                   completed.returncode, time.monotonic() - started,
                                   list(command), out_truncated or err_truncated)
        except subprocess.TimeoutExpired as exc:
            stdout, out_truncated = self._bound(exc.stdout)
            stderr, err_truncated = self._bound(exc.stderr)
            return ExecutionResult(False, stdout, (stderr + "\nTIMEOUT").strip(), -1,
                                   time.monotonic() - started, list(command),
                                   out_truncated or err_truncated, True)
        except OSError as exc:
            return ExecutionResult(False, "", f"EXECUTION_OS_ERROR:{type(exc).__name__}",
                                   -1, time.monotonic() - started, list(command))
