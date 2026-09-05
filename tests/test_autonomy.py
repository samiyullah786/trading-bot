import unittest

from src.domain import Mission, Criterion
from src.kernel import OutcomeKernel
from src.autonomy import AutonomousLoop, DeterministicStrategist

class AutonomyTests(unittest.TestCase):
    def test_cycle_creates_action_for_gap(self):
        mission = Mission.create("build", [Criterion("R1", "application works")])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        result = loop.cycle()
        self.assertEqual(result["state"], "READY")
        self.assertEqual(len(mission.actions), 1)

    def test_completed_mission_stops(self):
        mission = Mission.create("build", [Criterion("R1", "works", evidence=["proof"])])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        self.assertEqual(loop.cycle()["state"], "COMPLETE")

if __name__ == "__main__":
    unittest.main()
