import tempfile
import unittest

from src.execution import TerminalExecutor
from src.security import SecurityProfile


class ExecutionPolicyTests(unittest.TestCase):
    def test_allowlisted_executable_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = TerminalExecutor(directory, profile=SecurityProfile(allowed_executables=frozenset({"python"})))
            result = executor.run(["python", "-c", "print('ok')"])
            self.assertTrue(result.success)

    def test_denied_executable_never_reaches_process(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = TerminalExecutor(directory, profile=SecurityProfile(allowed_executables=frozenset({"python"})))
            with self.assertRaises(PermissionError):
                executor.run(["sh", "-c", "echo forbidden"])


if __name__ == "__main__":
    unittest.main()
