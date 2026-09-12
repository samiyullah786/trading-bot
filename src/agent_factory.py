from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable
import hashlib
import json
import time


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    risk: str = "LOW"


@dataclass
class AgentSpec:
    name: str
    purpose: str
    capabilities: list[str]
    success_tests: list[str] = field(default_factory=list)
    version: int = 1
    parent: str | None = None

    def fingerprint(self) -> str:
        body = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()[:16]


@dataclass
class Evaluation:
    passed: bool
    score: float
    evidence: list[str]
    failures: list[str]
    duration: float


class AgentFactory:
    """Create purpose-bound agents only after executable evaluation gates pass."""

    def __init__(self, capabilities: Iterable[Capability], evaluator: Callable[[AgentSpec], Evaluation] | None = None):
        self.capabilities = {c.name: c for c in capabilities}
        self.evaluator = evaluator
        self._lineage: dict[str, str | None] = {}

    def validate(self, spec: AgentSpec) -> None:
        if not spec.name.strip() or not spec.purpose.strip():
            raise ValueError("agent name and purpose are required")
        if not spec.capabilities:
            raise ValueError("agent requires at least one capability")
        unknown = sorted(set(spec.capabilities) - self.capabilities.keys())
        if unknown:
            raise ValueError(f"unknown capabilities: {unknown}")
        if len(spec.capabilities) > 128 or len(spec.success_tests) > 256:
            raise ValueError("agent specification exceeds bounds")
        if spec.version < 1:
            raise ValueError("agent version must be positive")

    def build(self, spec: AgentSpec) -> AgentSpec:
        self.validate(spec)
        built = AgentSpec(spec.name, spec.purpose, list(dict.fromkeys(spec.capabilities)), list(spec.success_tests), spec.version, spec.parent)
        self._lineage[built.name] = built.parent
        return built

    def improve(self, current: AgentSpec, candidates: Iterable[AgentSpec], minimum_score: float = 0.90) -> AgentSpec:
        self.validate(current)
        if not 0 <= minimum_score <= 1:
            raise ValueError("minimum_score must be between 0 and 1")
        best = current
        best_eval = self.evaluate(current)
        if not best_eval.passed or best_eval.score < minimum_score:
            raise ValueError("current agent does not meet the improvement baseline")
        for candidate in candidates:
            candidate.parent = current.name
            candidate.version = max(candidate.version, current.version + 1)
            self.validate(candidate)
            result = self.evaluate(candidate)
            if result.passed and result.score >= minimum_score and result.score > best_eval.score:
                best, best_eval = candidate, result
        self._lineage[best.name] = best.parent
        return best

    def evaluate(self, spec: AgentSpec) -> Evaluation:
        self.validate(spec)
        started = time.monotonic()
        if self.evaluator is None:
            return Evaluation(False, 0.0, [], ["no executable evaluator configured"], time.monotonic() - started)
        result = self.evaluator(spec)
        if not 0.0 <= result.score <= 1.0:
            raise ValueError("evaluator returned score outside 0..1")
        if result.duration < 0:
            raise ValueError("evaluator returned invalid duration")
        return result

    def lineage(self, name: str) -> list[str]:
        if name not in self._lineage:
            raise KeyError(name)
        chain: list[str] = []
        current: str | None = name
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                raise ValueError("agent lineage cycle detected")
            seen.add(current)
            chain.append(current)
            current = self._lineage.get(current)
        return chain


def default_capabilities() -> list[Capability]:
    return [
        Capability("filesystem", "inspect, create, edit and verify local project files"),
        Capability("terminal", "run bounded native processes and development commands", "MEDIUM"),
        Capability("browser", "operate an attached browser through CDP", "MEDIUM"),
        Capability("application", "launch and supervise installed local applications", "MEDIUM"),
        Capability("http", "use explicitly permitted HTTP APIs", "MEDIUM"),
        Capability("code", "plan, generate, test and repair software"),
        Capability("verification", "run evidence-producing checks and regressions"),
    ]
