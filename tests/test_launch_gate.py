import tempfile
import unittest
from pathlib import Path

from src.launch_gate import LaunchGate


class LaunchGateTests(unittest.TestCase):
    def test_valid_workspace_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            ready, results = LaunchGate(Path(directory)).run()
        self.assertTrue(ready)
        self.assertTrue(all(item.passed for item in results))

    def test_missing_workspace_fails_closed(self):
        ready, results = LaunchGate("/definitely/missing/aureon-workspace").run()
        self.assertFalse(ready)
        self.assertFalse(results[0].passed)


if __name__ == "__main__":
    unittest.main()
