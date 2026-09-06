from __future__ import annotations

from dataclasses import dataclass

@dataclass
class SelfAssessment:
    confidence: float
    known: list[str]
    unknown: list[str]
    next_information: str

class Metacognition:
    """Explicit uncertainty tracking for better planning."""

    def assess(self, known: list[str], unknown: list[str], confidence: float) -> SelfAssessment:
        confidence = max(0.0, min(1.0, confidence))
        next_information = unknown[0] if unknown else "no critical unknown identified"
        return SelfAssessment(confidence, known, unknown, next_information)

    def requires_research(self, assessment: SelfAssessment, threshold: float = 0.7) -> bool:
        return bool(assessment.unknown) and assessment.confidence < threshold
