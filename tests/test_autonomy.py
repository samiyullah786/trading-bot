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

    def test_executor_evidence_completes_mission(self):
        mission = Mission.create("build", [Criterion("R1", "works")])
        def executor(_):
            return True, "observed success", ["independent proof"]
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist(), executor)
        result = loop.run()
        self.assertEqual(result["result"]["state"], "COMPLETE")
        self.assertTrue(result["result"]["report"]["complete"])

    def test_failed_execution_does_not_claim_success(self):
        mission = Mission.create("build", [Criterion("R1", "works")])
        def executor(_):
            return False, "build failed", []
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist(), executor)
        result = loop.cycle()
        self.assertIn(result["state"], ("RECOVER", "BLOCKED"))
        self.assertFalse(OutcomeKernel(mission).verify())

if __name__ == "__main__":
    unittest.main()
