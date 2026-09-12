import unittest

from src.recovery_controller import RecoveryController


class RecoveryControllerTests(unittest.TestCase):
    def test_allows_changed_strategy_within_budget(self):
        controller = RecoveryController(max_attempts=2, max_replans=2)
        first = controller.decide("a1", "timeout", "timeout")
        self.assertTrue(first.allowed)
        self.assertEqual(first.attempts, 1)
        second = controller.decide("a2", "different failure", "execution")
        self.assertTrue(second.allowed)
        self.assertEqual(second.attempts, 1)
        third = controller.decide("a3", "another failure", "execution")
        self.assertFalse(third.allowed)
        self.assertEqual(third.reason, "REPLAN_BUDGET_EXHAUSTED")

    def test_repeated_evidence_hits_retry_budget_even_with_new_action_id(self):
        controller = RecoveryController(max_attempts=2, max_replans=8)
        self.assertTrue(controller.decide("a1", "same failure", "execution").allowed)
        self.assertTrue(controller.decide("a2", "same failure", "execution").allowed)
        decision = controller.decide("a3", "same failure", "execution")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "RETRY_BUDGET_EXHAUSTED")
        self.assertEqual(decision.attempts, 3)

    def test_configuration_and_dependency_fail_closed(self):
        controller = RecoveryController()
        for failure_class in ("configuration", "dependency"):
            decision = controller.decide("a1", "blocked", failure_class)
            self.assertFalse(decision.allowed)
            self.assertEqual(decision.reason, "NON_RETRYABLE_FAILURE")

    def test_unknown_failure_class_is_normalized(self):
        controller = RecoveryController(max_replans=1)
        decision = controller.decide("a1", "unexpected", "made-up")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.failure_class, "unknown")


if __name__ == "__main__":
    unittest.main()
