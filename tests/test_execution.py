import tempfile
import unittest
from pathlib import Path

from src.execution import TerminalExecutor
from src.filesystem import Workspace

class ExecutionTests(unittest.TestCase):
    def test_terminal_runs_python(self):
        with tempfile.TemporaryDirectory() as directory:
            result = TerminalExecutor(directory).run(["python", "-c", "print('ok')"])
            self.assertTrue(result.success)
            self.assertEqual(result.stdout.strip(), "ok")

    def test_workspace_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(directory)
            with self.assertRaises(PermissionError):
                workspace.read("../outside")

    def test_workspace_write_and_list(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(directory)
            workspace.write("nested/example.txt", "hello")
            self.assertTrue(workspace.exists("nested/example.txt"))
            self.assertEqual(workspace.list_files(), ["nested/example.txt"])

if __name__ == "__main__":
    unittest.main()
