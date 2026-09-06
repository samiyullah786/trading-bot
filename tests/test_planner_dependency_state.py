import unittest

from src.autonomy import AutonomousLoop, ProposedAction
from src.domain import Criterion, Mission, Status
from src.kernel import OutcomeKernel
from src.planner import CandidateAction, Planner


class DependencyStateTests(unittest.TestCase):
    def test_diverse_plans_accept_already_completed_dependencies(self):
        planner = Planner()
        prerequisite = CandidateAction("prepare", ["R1"], 0.8, 0.9, 0.0, 0.0)
        dependent = CandidateAction("execute", ["R2"], 0.8, 0.9, 0.0, 0.0, {"R1"})

        plans = planner.diverse_plans(
            [prerequisite, dependent],
            count=2,
            max_actions=2,
            completed={"R1"},
        )

        self.assertTrue(any(plan.actions and plan.actions[0].description == "execute" for plan in plans))

    def test_loop_does_not_block_when_dependency_is_already_verified(self):
        mission = Mission.create(
            "dependency mission",
            [
                Criterion("R1", "prepared", evidence=["proof"]),
                Criterion("R2", "executed"),
            ],
        )

        class Strategist:
            def propose(self, _mission, gaps):
                if "R2" in gaps:
                    yield ProposedAction(
                        "execute",
                        ["R2"],
                        depends_on=["R1"],
                        expected_progress=1.0,
                        success_probability=1.0,
                    )

        loop = AutonomousLoop(OutcomeKernel(mission), Strategist())
        result = loop.cycle()
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["action"], "A1")


if __name__ == "__main__":
    unittest.main()
