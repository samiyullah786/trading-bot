import tempfile
import unittest

from src.event_store import EventStore
from src.replay import EventReplayer


class ReplayTests(unittest.TestCase):
    def test_reconstructs_runtime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(f"{directory}/events.jsonl")
            store.append("agent_cycle", {"mission_id": "M1", "cycle": 1, "state": "PROGRESS"})
            store.append("action.created", {"mission_id": "M1", "action_id": "A1"})
            store.append("agent_cycle", {"mission_id": "M1", "cycle": 2, "state": "COMPLETE"})
            state = EventReplayer(store).verify_and_replay()
            self.assertEqual(state.mission_id, "M1")
            self.assertEqual(state.last_cycle, 2)
            self.assertEqual(state.state, "COMPLETE")
            self.assertEqual(state.actions, 1)


if __name__ == "__main__":
    unittest.main()
