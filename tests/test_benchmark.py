import unittest
from src.benchmark import CapabilityBenchmarks, BenchmarkResult

class BenchmarkTests(unittest.TestCase):
    def test_generality_requires_multiple_domains(self):
        benchmarks = CapabilityBenchmarks()
        benchmarks.record(BenchmarkResult("coding", 0.8, True, "software"))
        benchmarks.record(BenchmarkResult("planning", 0.6, True, "planning"))
        self.assertAlmostEqual(benchmarks.generality_score(), 0.7)

if __name__ == "__main__":
    unittest.main()
