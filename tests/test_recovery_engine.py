import unittest

from src.recovery_engine import EventDrivenRecovery, FailureMemory, RecoveryPlanner


class RecoveryEngineTests(unittest.TestCase):
    def test_failure_memory_deduplicates_observation(self):
        memory = FailureMemory()
        memory.record("A1", "timeout", 1)
        self.assertTrue(memory.seen("timeout"))
        self.assertFalse(memory.seen("different failure"))

    def test_timeout_produces_changed_strategy(self):
        planner = RecoveryPlanner()
        hypothesis = planner.next_strategy("command timeout")
        self.assertIsNotNone(hypothesis)
        self.assertEqual(hypothesis.strategy, "decompose_or_retry_with_larger_timeout")
        self.assertIsNone(planner.next_strategy("command timeout"))

    def test_event_driven_recovery(self):
        recovery = EventDrivenRecovery()
        plan = recovery.handle("action.failed", {"action_id": "A9", "observation": "permission denied", "attempt": 1})
        self.assertEqual(len(plan.hypotheses), 1)
        self.assertEqual(plan.hypotheses[0].strategy, "inspect_permissions")

    def test_irrelevant_event_is_noop(self):
        self.assertEqual(EventDrivenRecovery().handle("agent.started", {}).hypotheses, [])


if __name__ == "__main__":
    unittest.main()
