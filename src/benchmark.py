from __future__ import annotations

from dataclasses import dataclass, field
import statistics

@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    success: bool
    domain: str

class CapabilityBenchmarks:
    """Tracks measured capability across domains instead of capability claims."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def record(self, result: BenchmarkResult) -> None:
        if not 0.0 <= result.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
        self.results.append(result)

    def by_domain(self) -> dict[str, float]:
        domains: dict[str, list[float]] = {}
        for result in self.results:
            domains.setdefault(result.domain, []).append(result.score)
        return {domain: statistics.mean(scores) for domain, scores in domains.items()}

    def generality_score(self) -> float:
        values = list(self.by_domain().values())
        return statistics.mean(values) if values else 0.0
