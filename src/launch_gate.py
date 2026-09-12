from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


class LaunchGate:
    """Fail-closed preflight checks for a deployable autonomous runtime."""

    REQUIRED_MODULES = (
        "src.autonomy",
        "src.agent_runtime",
        "src.tool_runtime",
        "src.tools",
        "src.security",
    )

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()

    def check_workspace(self) -> GateResult:
        passed = self.workspace.is_dir() and os.access(self.workspace, os.R_OK | os.W_OK)
        return GateResult("workspace", passed, str(self.workspace))

    def check_python(self) -> GateResult:
        passed = sys.version_info >= (3, 11)
        return GateResult("python", passed, ".".join(map(str, sys.version_info[:3])))

    def check_modules(self) -> GateResult:
        failures: list[str] = []
        for name in self.REQUIRED_MODULES:
            try:
                importlib.import_module(name)
            except Exception as exc:
                failures.append(f"{name}:{type(exc).__name__}")
        return GateResult("imports", not failures, ";".join(failures) or "all required modules import")

    def run(self) -> tuple[bool, list[GateResult]]:
        results = [self.check_workspace(), self.check_python(), self.check_modules()]
        return all(item.passed for item in results), results
