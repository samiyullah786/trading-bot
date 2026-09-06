import unittest
from src.planner import CandidateAction, Planner


class PlannerAdvancedTests(unittest.TestCase):
    def test_build_plan_respects_dependencies(self):
        planner = Planner()
        prepare = CandidateAction("prepare", ["prepare"], 0.9, 0.9, 0.0, 0.0)
        deploy = CandidateAction("deploy", ["deploy"], 1.0, 0.9, 0.0, 0.0, {"prepare"})
        plan = planner.build_plan([deploy, prepare])
        self.assertEqual([a.description for a in plan.actions], ["prepare", "deploy"])

    def test_build_plan_respects_risk(self):
        planner = Planner()
        risky = CandidateAction("risky", ["x"], 1.0, 1.0, 0.0, 0.9)
        safe = CandidateAction("safe", ["x"], 0.7, 0.9, 0.0, 0.1)
        plan = planner.build_plan([risky, safe], max_risk=0.2)
        self.assertEqual(plan.actions[0].description, "safe")

    def test_diverse_plans_produces_alternatives(self):
        planner = Planner()
        candidates = [
            CandidateAction("a", ["a"], 0.9, 0.9, 0, 0),
            CandidateAction("b", ["b"], 0.8, 0.9, 0, 0),
            CandidateAction("c", ["c"], 0.7, 0.9, 0, 0),
        ]
        plans = planner.diverse_plans(candidates, count=2)
        self.assertEqual(len(plans), 2)
        self.assertNotEqual(
            tuple(a.description for a in plans[0].actions),
            tuple(a.description for a in plans[1].actions),
        )


if __name__ == "__main__":
    unittest.main()
