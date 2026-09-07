import unittest

from src.domain import Mission, Criterion
from src.kernel import OutcomeKernel
from src.autonomy import AutonomousLoop, DeterministicStrategist
from src.runtime import Runtime


class RuntimeTests(unittest.TestCase):
    def test_runtime_records_blocked_or_progress_state(self):
        mission = Mission.create("x", [Criterion("R1", "works")])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        result = Runtime(loop).run(maximum_cycles=1)
        self.assertIn(result["state"], ("PAUSED", "BLOCKED", "COMPLETE"))

    def test_runtime_resume_does_not_reuse_cycle_numbers(self):
        mission = Mission.create("x", [Criterion("R1", "works")])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        runtime = Runtime(loop)
        runtime.run(maximum_cycles=1)
        runtime.run(maximum_cycles=2)
        cycles = [entry.data["cycle"] for entry in runtime.ledger.entries if entry.kind == "cycle"]
        self.assertEqual(cycles, sorted(cycles))
        self.assertEqual(len(set(cycles)), len(cycles))


if __name__ == "__main__":
    unittest.main()
