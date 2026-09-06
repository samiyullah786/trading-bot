import tempfile
import unittest

from src.event_store import EventStore
from src.ledger import Ledger
from src.recovery import RecoveryEngine


class RecoveryDurabilityTests(unittest.TestCase):
    def test_repeated_observation_is_bounded_across_action_ids(self):
        recovery = RecoveryEngine()
        self.assertTrue(recovery.should_retry("A1", "same failure"))
        self.assertTrue(recovery.should_retry("A2", "same failure"))
        self.assertFalse(recovery.should_retry("A3", "same failure"))

    def test_ledger_is_persisted_as_hash_chained_events(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(f"{directory}/events.jsonl")
            ledger = Ledger(store)
            entry = ledger.append("agent_cycle", "PROGRESS", mission_id="m1", cycle=1)
            self.assertEqual(entry.sequence, 1)
            events = list(store.replay())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["kind"], "agent_cycle")
            store.verify()


if __name__ == "__main__":
    unittest.main()
