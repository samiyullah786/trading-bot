import unittest
from src.benchmark import BenchmarkGate, BenchmarkResult, CapabilityBenchmarks


class BenchmarkTests(unittest.TestCase):
    def test_generality_requires_multiple_domains(self):
        benchmarks = CapabilityBenchmarks()
        benchmarks.record(BenchmarkResult("coding", 0.8, True, "software"))
        benchmarks.record(BenchmarkResult("planning", 0.6, True, "planning"))
        self.assertAlmostEqual(benchmarks.generality_score(), 0.7)

    def test_gate_passes_when_required_domains_and_scores_are_met(self):
        benchmarks = CapabilityBenchmarks()
        benchmarks.record(BenchmarkResult("coding", 0.9, True, "software"))
        benchmarks.record(BenchmarkResult("planning", 0.85, True, "planning"))
        decision = benchmarks.gate(BenchmarkGate(
            minimum_general_score=0.8,
            minimum_domain_score=0.8,
            required_domains=("software", "planning"),
        ))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.failures, ())

    def test_gate_fails_closed_without_evidence(self):
        decision = CapabilityBenchmarks().gate(BenchmarkGate(required_domains=("software",)))
        self.assertFalse(decision.passed)
        self.assertIn("no benchmark evidence", decision.failures)
        self.assertIn("missing required domain: software", decision.failures)

    def test_gate_rejects_failed_benchmark_even_with_high_score(self):
        benchmarks = CapabilityBenchmarks()
        benchmarks.record(BenchmarkResult("coding", 1.0, False, "software"))
        decision = benchmarks.gate(BenchmarkGate(minimum_general_score=0.9))
        self.assertFalse(decision.passed)
        self.assertTrue(any("failed benchmarks" in item for item in decision.failures))


if __name__ == "__main__":
    unittest.main()
