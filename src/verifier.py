from __future__ import annotations

from dataclasses import dataclass
from .kernel import OutcomeKernel

@dataclass
class VerificationResult:
    complete: bool
    verified: list[str]
    missing: list[str]

class MissionVerifier:
    def verify(self, kernel: OutcomeKernel) -> VerificationResult:
        kernel.verify()
        verified = []
        missing = []
        for criterion in kernel.mission.criteria:
            if criterion.mandatory:
                (verified if criterion.evidence else missing).append(criterion.id)
        return VerificationResult(
            complete=not missing,
            verified=verified,
            missing=missing,
        )
