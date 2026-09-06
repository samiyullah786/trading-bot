import unittest

from src.autonomy import AutonomousLoop, ProposedAction
from src.domain import Criterion, Mission
from src.kernel import OutcomeKernel
from src.recovery_engine import RecoveryHypothesis, RecoveryPlan


class RecoveryAwareStrategist:
    def __init__(self):
        self.recovery = []

    def propose(self, mission, gaps):
        yield ProposedAction("initial", gaps[:1], expected_progress=1.0, success_probability=1.0)

    def propose_with_recovery(self, mission, gaps, recovery):
        self.recovery = recovery
        yield ProposedAction("recovered", gaps[:1], expected_progress=1.0, success_probability=1.0)


class RecoveryReplanningTests(unittest.TestCase):
    def test_recovery_is_consumed_by_next_cycle(self):
        mission = Mission.create("recover", [Criterion("R1", "done")])
        strategist = RecoveryAwareStrategist()
        loop = AutonomousLoop(OutcomeKernel(mission), strategist)
        loop.apply_recovery(RecoveryPlan([RecoveryHypothesis("change", "alternative_strategy", 0.8)]))
        result = loop.cycle()
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["description"], "recovered")
        self.assertEqual(str(strategist.recovery[0].strategy), "alternative_strategy")


if __name__ == "__main__":
    unittest.main()
