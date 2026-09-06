import tempfile
import unittest
from pathlib import Path

from src.event_store import EventStore


class EventStoreTests(unittest.TestCase):
    def test_append_replay_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            first = store.append("MISSION_CREATED", {"mission_id": "m1"})
            second = store.append("ACTION_COMPLETED", {"action_id": "a1"})

            events = store.events()
            self.assertEqual([event.sequence for event in events], [1, 2])
            self.assertEqual(second.previous_hash, first.hash)
            store.verify()
            self.assertEqual(store.snapshot()["count"], 2)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("TEST", {"value": 1})
            text = path.read_text(encoding="utf-8").replace('"value":1', '"value":2')
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                store.verify()

    def test_empty_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            store.verify()
            self.assertEqual(store.snapshot()["last_sequence"], 0)


if __name__ == "__main__":
    unittest.main()
