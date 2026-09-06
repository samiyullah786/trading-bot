from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import urllib.request

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    evidence: str

class IndependentVerifier:
    """Evidence-producing checks that do not trust the planner's declaration."""
    def file_hash(self, path: str, expected_sha256: str) -> CheckResult:
        data = Path(path).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        return CheckResult("file_hash", actual == expected_sha256, f"sha256={actual}")

    def file_exists(self, path: str) -> CheckResult:
        exists = Path(path).is_file()
        return CheckResult("file_exists", exists, f"path={path}; exists={exists}")

    def http_status(self, url: str, expected: int = 200, timeout: float = 10.0) -> CheckResult:
        parsed = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AUREON/1.0"})
        with urllib.request.urlopen(parsed, timeout=timeout) as response:
            status = response.status
        return CheckResult("http_status", status == expected, f"status={status}; url={url}")

    def all_passed(self, checks: list[CheckResult]) -> bool:
        return bool(checks) and all(check.passed for check in checks)
