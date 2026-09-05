from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

@dataclass
class Failure:
    action_id: str
    observation: str
    fingerprint: str
    attempts: int = 1

class RecoveryEngine:
    """Prevents blind retry loops.

    A repeated failure fingerprint requires a changed hypothesis or new
    observation before another equivalent attempt is considered useful.
    """

    def __init__(self):
        self.failures: dict[str, Failure] = {}

    @staticmethod
    def fingerprint(observation: str) -> str:
        normalized = " ".join(observation.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def record(self, action_id: str, observation: str) -> Failure:
        key = f"{action_id}:{self.fingerprint(observation)}"
        if key in self.failures:
            self.failures[key].attempts += 1
            return self.failures[key]
        failure = Failure(action_id, observation, key)
        self.failures[key] = failure
        return failure

    def should_retry(self, action_id: str, observation: str, maximum: int = 2) -> bool:
        failure = self.record(action_id, observation)
        return failure.attempts <= maximum
