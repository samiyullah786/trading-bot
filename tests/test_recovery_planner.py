import unittest

from src.agent_controller import ControllerDecision
from src.autonomy import ProposedAction
from src.recovery_controller import RecoveryController
from src.recovery_planner import RecoveryPlanner


class StubController:
    def __init__(self, actions):
        self.actions = actions
        self.calls = []

    def decide(self, objective, context, constraints):
        self.calls.append((objective, context, constraints))
        return ControllerDecision(self.actions, 0.9, [], False)


class RecoveryPlannerTests(unittest.TestCase):
    def failed_action(self, command=("python", "-c", "raise SystemExit(1)")):
        return ProposedAction(
            description="failed step",
            criterion_ids=["c1"],
            command=list(command),
            expected_observation="success",
            action_id="failed-1",
        )

    def test_replans_with_changed_strategy_and_preserves_failure_context(self):
        candidate = ProposedAction(
            description="use an alternate verification path",
            criterion_ids=["c1"],
            command=["python", "-c", "print('alternate')"],
            expected_observation="alternate",
            action_id="recovery-1",
        )
        controller = StubController([candidate])
        planner = RecoveryPlanner(controller, RecoveryController(max_replans=1))
        plan = planner.replan("finish task", {"workspace": "/tmp"}, self.failed_action(), "exit=1", "execution")
        self.assertTrue(plan.allowed)
        self.assertEqual(plan.reason, "RECOVERY_PLAN_VALIDATED")
        self.assertEqual(plan.actions, (candidate,))
        self.assertIn("Do not repeat the failed action command unchanged.", controller.calls[0][2])

    def test_rejects_unchanged_strategy(self):
        failed = self.failed_action()
        controller = StubController([self.failed_action()])
        planner = RecoveryPlanner(controller, RecoveryController(max_replans=1))
        plan = planner.replan("finish task", {}, failed, "exit=1", "execution")
        self.assertFalse(plan.allowed)
        self.assertEqual(plan.reason, "UNCHANGED_STRATEGY_REJECTED")

    def test_rejects_invalid_candidate_plan(self):
        candidate = ProposedAction("candidate", ["c1"], command=["echo", "ok"], action_id="r1")
        controller = StubController([candidate])
        planner = RecoveryPlanner(
            controller,
            RecoveryController(max_replans=1),
            action_validator=lambda actions: "DEPENDENCY_CYCLE",
        )
        plan = planner.replan("finish", {}, self.failed_action(), "failure", "execution")
        self.assertFalse(plan.allowed)
        self.assertEqual(plan.reason, "INVALID_RECOVERY_PLAN:DEPENDENCY_CYCLE")

    def test_respects_recovery_budget(self):
        candidate = ProposedAction("candidate", ["c1"], command=["echo", "ok"], action_id="r1")
        controller = StubController([candidate])
        planner = RecoveryPlanner(controller, RecoveryController(max_replans=1))
        first = planner.replan("finish", {}, self.failed_action(), "first", "execution")
        second = planner.replan("finish", {}, self.failed_action(("echo", "second")), "second", "execution")
        self.assertTrue(first.allowed)
        self.assertFalse(second.allowed)
        self.assertEqual(second.reason, "REPLAN_BUDGET_EXHAUSTED")


if __name__ == "__main__":
    unittest.main()
