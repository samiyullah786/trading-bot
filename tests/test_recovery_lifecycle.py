import unittest

from src.agent_controller import ControllerDecision
from src.autonomy import ProposedAction
from src.recovery_controller import RecoveryController
from src.recovery_lifecycle import RecoveryLifecycle
from src.recovery_planner import RecoveryPlanner


class StubController:
    def __init__(self, actions):
        self.actions = actions

    def decide(self, objective, context, constraints):
        return ControllerDecision(self.actions, 0.9, [], False)


class RecoveryLifecycleTests(unittest.TestCase):
    def failed(self, action_id="failed"):
        return ProposedAction("failed", ["c1"], command=["python", "-c", "raise SystemExit(1)"], action_id=action_id)

    def test_accepts_new_recovery_actions_and_keeps_verified_work(self):
        verified = ProposedAction("verified", ["c1"], command=["echo", "verified"], action_id="v1")
        candidate = ProposedAction("alternate", ["c1"], command=["echo", "alternate"], action_id="r1")
        planner = RecoveryPlanner(StubController([candidate]), RecoveryController(max_replans=1))
        lifecycle = RecoveryLifecycle(planner)
        result = lifecycle.recover("finish", {}, [verified, self.failed()], self.failed(), "exit=1", "execution")
        self.assertTrue(result.allowed)
        self.assertEqual(result.actions, (candidate,))
        self.assertEqual(lifecycle.records[-1].decision, "RECOVERY_ACCEPTED")

    def test_rejects_action_id_collision(self):
        existing = ProposedAction("existing", ["c1"], command=["echo", "x"], action_id="same")
        candidate = ProposedAction("replacement", ["c1"], command=["echo", "y"], action_id="same")
        planner = RecoveryPlanner(StubController([candidate]), RecoveryController(max_replans=1))
        lifecycle = RecoveryLifecycle(planner)
        result = lifecycle.recover("finish", {}, [existing], self.failed(), "failure", "execution")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "RECOVERY_ACTION_ID_COLLISION")

    def test_rejects_duplicate_candidate_ids(self):
        a = ProposedAction("a", ["c1"], command=["echo", "a"], action_id="r")
        b = ProposedAction("b", ["c1"], command=["echo", "b"], action_id="r")
        planner = RecoveryPlanner(StubController([a, b]), RecoveryController(max_replans=1))
        lifecycle = RecoveryLifecycle(planner)
        result = lifecycle.recover("finish", {}, [], self.failed(), "failure", "execution")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "RECOVERY_DUPLICATE_ACTION_ID")

    def test_non_retryable_failure_is_recorded(self):
        candidate = ProposedAction("candidate", ["c1"], command=["echo", "ok"], action_id="r1")
        planner = RecoveryPlanner(StubController([candidate]), RecoveryController())
        lifecycle = RecoveryLifecycle(planner)
        result = lifecycle.recover("finish", {}, [], self.failed(), "missing dependency", "dependency")
        self.assertFalse(result.allowed)
        self.assertEqual(lifecycle.records[-1].decision, "NON_RETRYABLE_FAILURE")


if __name__ == "__main__":
    unittest.main()
