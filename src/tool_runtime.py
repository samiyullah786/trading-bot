from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .tools import ToolRegistry, ToolRequest, ToolResult


@dataclass(frozen=True)
class Verification:
    passed: bool
    evidence: tuple[str, ...] = ()
    observation: str = ""


@dataclass
class ToolExecution:
    success: bool
    observation: str
    evidence: list[str] = field(default_factory=list)
    attempts: int = 0
    verification: Verification | None = None
    failure_class: str | None = None


class ToolRuntime:
    """Bounded plan -> tool -> observe -> verify -> retry execution boundary."""

    def __init__(self, registry: ToolRegistry, verifier: Callable[[ToolRequest, ToolResult], Verification] | None = None, max_attempts: int = 2, max_observation: int = 12000) -> None:
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if max_observation < 256:
            raise ValueError("max_observation must be at least 256")
        self.registry = registry
        self.verifier = verifier
        self.max_attempts = max_attempts
        self.max_observation = max_observation

    def execute(self, tool_name: str, request: ToolRequest) -> ToolExecution:
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name must not be empty")
        last_observation = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.registry.execute(tool_name, request)
            except KeyError as exc:
                return ToolExecution(False, f"UNKNOWN_TOOL:{exc}", attempts=attempt, failure_class="configuration")
            except Exception as exc:
                last_observation = f"EXECUTION_ERROR:{type(exc).__name__}:{exc}"
                if attempt == self.max_attempts:
                    return ToolExecution(False, last_observation[: self.max_observation], attempts=attempt, failure_class="exception")
                continue
            observation = (result.observation or "")[: self.max_observation]
            evidence = [str(item)[: self.max_observation] for item in result.evidence]
            last_observation = observation
            if not result.success:
                if attempt == self.max_attempts:
                    return ToolExecution(False, observation, evidence, attempt, failure_class="tool_failure")
                continue
            try:
                verification = self.verifier(request, result) if self.verifier else Verification(bool(evidence), tuple(evidence), observation)
            except Exception as exc:
                verification = Verification(False, tuple(evidence), f"VERIFICATION_ERROR:{type(exc).__name__}")
            if verification.passed:
                merged = evidence + [item for item in verification.evidence if item not in evidence]
                return ToolExecution(True, observation, merged, attempt, verification)
            if attempt == self.max_attempts:
                return ToolExecution(False, verification.observation or observation, evidence, attempt, verification, "verification_failure")
        return ToolExecution(False, last_observation, attempts=self.max_attempts, failure_class="exhausted")
