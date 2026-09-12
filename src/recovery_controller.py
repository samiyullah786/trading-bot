from __future__ import annotations

from dataclasses import dataclass

from .recovery import Failure, RecoveryEngine


@dataclass(frozen=True)
class RecoveryDecision:
    allowed: bool
    reason: str
    attempts: int
    failure_class: str


class RecoveryController:
    """Bound autonomous recovery without permitting blind or infinite retries."""

    _MAX_CLASSES = {"configuration", "dependency", "execution", "verification", "timeout", "unknown"}
    _NON_RETRYABLE = {"configuration", "dependency"}

    def __init__(self, engine: RecoveryEngine | None = None, *, max_attempts: int = 2, max_replans: int = 3) -> None:
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if max_replans < 0 or max_replans > 8:
            raise ValueError("max_replans must be between 0 and 8")
        self.engine = engine or RecoveryEngine()
        self.max_attempts = max_attempts
        self.max_replans = max_replans
        self.replans = 0

    def decide(self, action_id: str, observation: str, failure_class: str = "unknown") -> RecoveryDecision:
        normalized = str(failure_class).strip().lower() or "unknown"
        if normalized not in self._MAX_CLASSES:
            normalized = "unknown"
        failure = self.engine.record(str(action_id), str(observation))
        if normalized in self._NON_RETRYABLE:
            return RecoveryDecision(False, "NON_RETRYABLE_FAILURE", failure.attempts, normalized)
        if failure.attempts > self.max_attempts:
            return RecoveryDecision(False, "RETRY_BUDGET_EXHAUSTED", failure.attempts, normalized)
        if self.replans >= self.max_replans:
            return RecoveryDecision(False, "REPLAN_BUDGET_EXHAUSTED", failure.attempts, normalized)
        self.replans += 1
        return RecoveryDecision(True, "RECOVERY_ALLOWED_WITH_CHANGED_STRATEGY", failure.attempts, normalized)

    def reset_replan_budget(self) -> None:
        self.replans = 0

    def export_state(self) -> dict:
        return {
            "replans": self.replans,
            "failures": [
                {
                    "action_id": failure.action_id,
                    "observation": failure.observation,
                    "fingerprint": failure.fingerprint,
                    "attempts": failure.attempts,
                }
                for failure in self.engine.failures.values()
            ],
        }

    def restore_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            raise ValueError("recovery state must be an object")
        replans = state.get("replans", 0)
        failures = state.get("failures", [])
        if not isinstance(replans, int) or isinstance(replans, bool) or not 0 <= replans <= self.max_replans:
            raise ValueError("invalid recovery replan count")
        if not isinstance(failures, list):
            raise ValueError("invalid recovery failures")
        restored: dict[str, Failure] = {}
        for item in failures:
            if not isinstance(item, dict):
                continue
            action_id = item.get("action_id")
            observation = item.get("observation")
            fingerprint = item.get("fingerprint")
            attempts = item.get("attempts", 1)
            if not all(isinstance(value, str) for value in (action_id, observation, fingerprint)):
                continue
            if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1 or attempts > 100:
                continue
            if fingerprint != self.engine.fingerprint(observation):
                continue
            restored[fingerprint] = Failure(action_id, observation, fingerprint, attempts)
        self.engine.failures = restored
        self.replans = replans
