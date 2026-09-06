from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Callable, Iterable


@dataclass(frozen=True)
class FailureObservation:
    action_id: str
    observation: str
    fingerprint: str
    attempt: int


@dataclass(frozen=True)
class RecoveryHypothesis:
    description: str
    strategy: str
    expected_improvement: float
    risk: float = 0.0


@dataclass
class RecoveryPlan:
    hypotheses: list[RecoveryHypothesis] = field(default_factory=list)


class FailureMemory:
    """Cross-action failure memory used to avoid repeating the same mistake."""

    def __init__(self) -> None:
        self.observations: list[FailureObservation] = []
        self._fingerprints: set[str] = set()

    @staticmethod
    def fingerprint(observation: str) -> str:
        return hashlib.sha256(observation.strip().encode("utf-8")).hexdigest()

    def record(self, action_id: str, observation: str, attempt: int) -> FailureObservation:
        item = FailureObservation(action_id, observation, self.fingerprint(observation), attempt)
        self.observations.append(item)
        self._fingerprints.add(item.fingerprint)
        return item

    def seen(self, observation: str) -> bool:
        return self.fingerprint(observation) in self._fingerprints


class RecoveryPlanner:
    """Generate bounded alternative recovery hypotheses from observed failures."""

    def __init__(self, memory: FailureMemory | None = None):
        self.memory = memory or FailureMemory()

    def plan(self, failures: Iterable[FailureObservation]) -> RecoveryPlan:
        items = list(failures)
        hypotheses: list[RecoveryHypothesis] = []
        for failure in items:
            text = failure.observation.lower()
            if "timeout" in text:
                hypotheses.append(RecoveryHypothesis(
                    "Increase timeout or split the operation into smaller steps",
                    "decompose_or_retry_with_larger_timeout", 0.7, 0.2,
                ))
            elif "not found" in text or "no such file" in text:
                hypotheses.append(RecoveryHypothesis(
                    "Discover the missing resource before retrying",
                    "discover_then_execute", 0.8, 0.1,
                ))
            elif "permission" in text or "access denied" in text:
                hypotheses.append(RecoveryHypothesis(
                    "Inspect permissions and choose a permitted workspace operation",
                    "inspect_permissions", 0.65, 0.15,
                ))
            else:
                hypotheses.append(RecoveryHypothesis(
                    "Change the execution strategy rather than repeating the failed action",
                    "alternative_strategy", 0.5, 0.2,
                ))
        unique: dict[str, RecoveryHypothesis] = {}
        for item in hypotheses:
            unique.setdefault(item.strategy, item)
        return RecoveryPlan(sorted(unique.values(), key=lambda x: x.expected_improvement - x.risk, reverse=True))

    def next_strategy(self, observation: str) -> RecoveryHypothesis | None:
        fingerprint = self.memory.fingerprint(observation)
        if fingerprint in self.memory._fingerprints:
            return None
        failure = self.memory.record("recovery", observation, len(self.memory.observations) + 1)
        return self.plan([failure]).hypotheses[0]


class EventDrivenRecovery:
    """Translate runtime failure events into recovery decisions."""

    def __init__(self, planner: RecoveryPlanner | None = None):
        self.planner = planner or RecoveryPlanner()

    def handle(self, event_type: str, payload: dict) -> RecoveryPlan:
        if event_type not in {"action.failed", "executor.failed", "verification.failed"}:
            return RecoveryPlan()
        observation = str(payload.get("observation") or payload.get("error") or "unknown failure")
        failure = self.planner.memory.record(
            str(payload.get("action_id", "unknown")),
            observation,
            int(payload.get("attempt", 1)),
        )
        return self.planner.plan([failure])
