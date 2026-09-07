import json
import tempfile
import unittest
from pathlib import Path

from src.event_store import EventStore


class EventStoreIntegrityTests(unittest.TestCase):
    def test_hash_chain_detects_payload_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("action.started", {"action_id": "a1"})
            store.append("action.completed", {"action_id": "a1"})
            lines = path.read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0])
            event["payload"]["action_id"] = "evil"
            lines[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.verify()

    def test_hash_chain_detects_reordering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("one")
            store.append("two")
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.verify()

    def test_secret_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("tool.completed", {"api_token": "super-secret-token-12345678901234567890"})
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("super-secret-token", raw)
            self.assertIn("[REDACTED]", raw)

    def test_oversized_payload_is_replaced_with_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            event = store.append("large", {"output": "x" * 100_000})
            self.assertTrue(event.payload["_payload_truncated"])
            self.assertIn("_payload_sha256", event.payload)
            store.verify()


if __name__ == "__main__":
    unittest.main()
