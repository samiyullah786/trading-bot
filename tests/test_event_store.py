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
            self.assertEqual(len(list(store.replay())), 2)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("TEST", {"value": 1})
            text = path.read_text(encoding="utf-8").replace('"value":1', '"value":2')
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                store.verify()

    def test_secret_keys_and_values_are_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            event = store.append("CREDENTIAL_TEST", {
                "api_key": "super-secret-value",
                "message": "token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "safe": "visible",
            })
            self.assertEqual(event.payload["api_key"], "[REDACTED]")
            self.assertEqual(event.payload["message"], "token [REDACTED]")
            self.assertEqual(event.payload["safe"], "visible")

    def test_oversized_payload_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            event = store.append("LARGE", {"blob": "x" * 100_000})
            self.assertTrue(event.payload["_payload_truncated"])
            self.assertIn("_payload_sha256", event.payload)
            store.verify()

    def test_empty_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            store.verify()
            self.assertEqual(store.snapshot()["last_sequence"], 0)


if __name__ == "__main__":
    unittest.main()
