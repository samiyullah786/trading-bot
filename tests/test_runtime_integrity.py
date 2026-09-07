import tempfile
import unittest
from pathlib import Path

from src.event_store import EventStore
from src.runtime_integrity import RuntimeIntegrity


class RuntimeIntegrityTests(unittest.TestCase):
    def test_valid_store_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.jsonl")
            store.append("mission.started", {"mission": "x"})
            report = RuntimeIntegrity(store).check()
            self.assertTrue(report.valid)
            self.assertEqual(report.event_count, 1)

    def test_tampered_store_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            store = EventStore(path)
            store.append("mission.started", {"mission": "x"})
            raw = path.read_text(encoding="utf-8").replace('"mission":"x"', '"mission":"tampered"')
            path.write_text(raw, encoding="utf-8")
            integrity = RuntimeIntegrity(store)
            report = integrity.check()
            self.assertFalse(report.valid)
            with self.assertRaises(RuntimeError):
                integrity.require_valid()

    def test_corrupt_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            report = RuntimeIntegrity(EventStore(path)).check()
            self.assertFalse(report.valid)


if __name__ == "__main__":
    unittest.main()
