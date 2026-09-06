from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import subprocess
import urllib.request


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    evidence: str


class IndependentVerifier:
    """Evidence-producing checks that do not trust the planner's declaration."""

    def file_hash(self, path: str, expected_sha256: str) -> CheckResult:
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            return CheckResult("file_hash", False, f"read_error={type(exc).__name__}: {exc}")
        actual = hashlib.sha256(data).hexdigest()
        return CheckResult("file_hash", actual == expected_sha256, f"sha256={actual}")

    def file_exists(self, path: str) -> CheckResult:
        exists = Path(path).is_file()
        return CheckResult("file_exists", exists, f"path={path}; exists={exists}")

    def command(self, argv: list[str], cwd: str | None = None, timeout: float = 30.0) -> CheckResult:
        if not argv or not all(isinstance(x, str) and x for x in argv):
            return CheckResult("command", False, "invalid argv")
        try:
            result = subprocess.run(argv, cwd=cwd, shell=False, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckResult("command", False, f"execution_error={type(exc).__name__}: {exc}")
        evidence = f"returncode={result.returncode}; stdout={result.stdout[-2000:]}; stderr={result.stderr[-2000:]}"
        return CheckResult("command", result.returncode == 0, evidence)

    def http_status(self, url: str, expected: int = 200, timeout: float = 10.0) -> CheckResult:
        try:
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AUREON/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
            return CheckResult("http_status", status == expected, f"status={status}; url={url}")
        except Exception as exc:
            return CheckResult("http_status", False, f"request_error={type(exc).__name__}: {exc}")

    def all_passed(self, checks: list[CheckResult]) -> bool:
        return bool(checks) and all(check.passed for check in checks)
