import unittest

from src.autonomy import AutonomousLoop, ProposedAction
from src.domain import Criterion, Mission, Status
from src.kernel import OutcomeKernel


class SequenceStrategist:
    def __init__(self, actions):
        self.actions = actions

    def propose(self, mission, gaps):
        return [action for action in self.actions if set(action.criterion_ids) & set(gaps)]


class DynamicPlanningTests(unittest.TestCase):
    def test_planner_selects_highest_value_candidate(self):
        mission = Mission.create("complete work", [Criterion("c1", "work")])
        actions = [
            ProposedAction("cheap", ["c1"], command=["python", "-c", "print('cheap')"], expected_progress=0.5, success_probability=0.8, cost=0.1),
            ProposedAction("strong", ["c1"], command=["python", "-c", "print('strong')"], expected_progress=1.0, success_probability=1.0, cost=0.1),
        ]
        seen = []
        def executor(action):
            seen.append(action.description)
            return True, "ok", ["verified evidence"]

        result = AutonomousLoop(OutcomeKernel(mission), SequenceStrategist(actions), executor).run(3)
        self.assertEqual(result["result"]["state"], "COMPLETE")
        self.assertEqual(seen, ["strong"])

    def test_failure_forces_replan_to_different_candidate(self):
        mission = Mission.create("complete work", [Criterion("c1", "work")])
        actions = [
            ProposedAction("first", ["c1"], command=["python", "-c", "raise SystemExit(1)"], expected_progress=1.0, success_probability=1.0),
            ProposedAction("fallback", ["c1"], command=["python", "-c", "print('fallback')"], expected_progress=0.9, success_probability=0.9),
        ]
        seen = []
        def executor(action):
            seen.append(action.description)
            if action.description == "first":
                return False, "failure", []
            return True, "ok", ["verified evidence"]

        result = AutonomousLoop(OutcomeKernel(mission), SequenceStrategist(actions), executor).run(4)
        self.assertEqual(result["result"]["state"], "COMPLETE")
        self.assertEqual(seen, ["first", "fallback"])

    def test_dependency_blocks_until_requirement_is_verified(self):
        mission = Mission.create("complete work", [Criterion("c1", "prepare"), Criterion("c2", "finish")])
        actions = [
            ProposedAction("finish", ["c2"], depends_on=["c1"], expected_progress=1.0, success_probability=1.0),
            ProposedAction("prepare", ["c1"], expected_progress=0.6, success_probability=1.0),
        ]
        loop = AutonomousLoop(OutcomeKernel(mission), SequenceStrategist(actions), lambda action: (True, "ok", ["evidence"]))
        first = loop.cycle()
        self.assertEqual(first["action"], "A1")
        self.assertEqual(mission.actions[0].criterion_ids, ["c1"])
        self.assertEqual(mission.criteria[0].status, Status.VERIFIED)
        second = loop.cycle()
        self.assertEqual(second["state"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
