from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass
class Failure:
    action_id: str
    observation: str
    fingerprint: str
    attempts: int = 1


class RecoveryEngine:
    """Prevent blind retries and require changed evidence for repetition."""

    def __init__(self):
        # Fingerprint is deliberately independent of action id: replanning a
        # failed action must not reset the retry budget by assigning a new id.
        self.failures: dict[str, Failure] = {}

    @staticmethod
    def fingerprint(observation: str) -> str:
        normalized = " ".join(observation.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def record(self, action_id: str, observation: str) -> Failure:
        fingerprint = self.fingerprint(observation)
        if fingerprint in self.failures:
            failure = self.failures[fingerprint]
            failure.attempts += 1
            failure.action_id = action_id
            failure.observation = observation
            return failure
        failure = Failure(action_id, observation, fingerprint)
        self.failures[fingerprint] = failure
        return failure

    def should_retry(self, action_id: str, observation: str, maximum: int = 2) -> bool:
        if maximum < 1:
            raise ValueError("maximum must be positive")
        failure = self.record(action_id, observation)
        return failure.attempts <= maximum
