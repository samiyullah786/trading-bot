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

if __name__ == "__main__":
    unittest.main()
