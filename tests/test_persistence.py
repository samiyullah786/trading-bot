import tempfile
import unittest
from src.persistence import JsonStore

class PersistenceTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JsonStore(directory)
            store.save("mission", {"state":"RUNNING"})
            self.assertEqual(store.load("mission")["state"], "RUNNING")

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                JsonStore(directory).save("../escape", {})

if __name__ == "__main__":
    unittest.main()
