from __future__ import annotations

from dataclasses import dataclass
import statistics


@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    success: bool
    domain: str


@dataclass(frozen=True)
class BenchmarkGate:
    """Objective release gate over measured benchmark evidence."""

    minimum_general_score: float = 0.80
    minimum_domain_score: float = 0.70
    required_domains: tuple[str, ...] = ()
    require_success: bool = True


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    score: float
    domain_scores: dict[str, float]
    failures: tuple[str, ...]


class CapabilityBenchmarks:
    """Tracks measured capability across domains instead of capability claims."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def record(self, result: BenchmarkResult) -> None:
        if not isinstance(result.benchmark, str) or not result.benchmark.strip():
            raise ValueError("benchmark name is required")
        if not isinstance(result.domain, str) or not result.domain.strip():
            raise ValueError("benchmark domain is required")
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

    def gate(self, policy: BenchmarkGate | None = None) -> GateDecision:
        policy = policy or BenchmarkGate()
        if not 0.0 <= policy.minimum_general_score <= 1.0:
            raise ValueError("minimum_general_score must be between 0 and 1")
        if not 0.0 <= policy.minimum_domain_score <= 1.0:
            raise ValueError("minimum_domain_score must be between 0 and 1")
        domains = self.by_domain()
        failures: list[str] = []
        score = self.generality_score()
        if not self.results:
            failures.append("no benchmark evidence")
        if score < policy.minimum_general_score:
            failures.append(f"generality score {score:.3f} < {policy.minimum_general_score:.3f}")
        for domain in policy.required_domains:
            if domain not in domains:
                failures.append(f"missing required domain: {domain}")
            elif domains[domain] < policy.minimum_domain_score:
                failures.append(
                    f"domain {domain} score {domains[domain]:.3f} < {policy.minimum_domain_score:.3f}"
                )
        if policy.require_success:
            failed_runs = [r.benchmark for r in self.results if not r.success]
            if failed_runs:
                failures.append(f"failed benchmarks: {','.join(sorted(failed_runs))}")
        return GateDecision(not failures, score, domains, tuple(failures))
