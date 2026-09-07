import sys
import tempfile
import unittest

from src.execution import TerminalExecutor
from src.security import SecurityProfile


class ExecutionTests(unittest.TestCase):
    def test_terminal_runs_python(self):
        with tempfile.TemporaryDirectory() as directory:
            result = TerminalExecutor(directory).run([sys.executable, "-c", "print('ok')"])
            self.assertTrue(result.success)
            self.assertEqual(result.stdout.strip(), "ok")

    def test_timeout_is_bounded_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = SecurityProfile(timeout_seconds=0.1)
            result = TerminalExecutor(directory, profile=profile).run(
                [sys.executable, "-c", "import time; print('partial'); time.sleep(2)"]
            )
            self.assertFalse(result.success)
            self.assertTrue(result.timed_out)
            self.assertIn("TIMEOUT", result.stderr)

    def test_timeout_byte_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = SecurityProfile(timeout_seconds=0.1)
            result = TerminalExecutor(directory, profile=profile).run(
                [sys.executable, "-c", "import sys,time; sys.stdout.write('partial'); sys.stdout.flush(); time.sleep(2)"]
            )
            self.assertTrue(result.timed_out)
            self.assertIn("partial", result.stdout)

    def test_output_is_truncated(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = SecurityProfile(max_output_bytes=32)
            result = TerminalExecutor(directory, profile=profile).run(
                [sys.executable, "-c", "print('x' * 1000)"]
            )
            self.assertTrue(result.success)
            self.assertTrue(result.truncated)
            self.assertLessEqual(len(result.stdout.encode("utf-8")), 32)

    def test_missing_workspace_fails_closed(self):
        with self.assertRaises(ValueError):
            TerminalExecutor("/definitely/not/a/workspace")


if __name__ == "__main__":
    unittest.main()
