import os
import tempfile
import unittest

from src.execution import TerminalExecutor
from src.security import SecurityProfile


class ExecutionSecurityTests(unittest.TestCase):
    def test_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = TerminalExecutor(
                directory,
                profile=SecurityProfile(max_output_bytes=32),
            )
            result = executor.run(["python", "-c", "print('x' * 1000)"])
            self.assertTrue(result.success)
            self.assertTrue(result.truncated)
            self.assertLessEqual(len(result.stdout.encode()), 32)

    def test_sensitive_environment_is_not_inherited(self):
        with tempfile.TemporaryDirectory() as directory:
            old = os.environ.get("AUREON_TEST_SECRET")
            os.environ["AUREON_TEST_SECRET"] = "do-not-leak"
            try:
                executor = TerminalExecutor(directory)
                result = executor.run([
                    "python", "-c", "import os; print(os.getenv('AUREON_TEST_SECRET', 'MISSING'))"
                ])
                self.assertTrue(result.success)
                self.assertIn("MISSING", result.stdout)
            finally:
                if old is None:
                    os.environ.pop("AUREON_TEST_SECRET", None)
                else:
                    os.environ["AUREON_TEST_SECRET"] = old


if __name__ == "__main__":
    unittest.main()
