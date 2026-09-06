import tempfile
import unittest

from src.builtin_tools import TerminalTool
from src.command_router import CommandRouter
from src.execution import TerminalExecutor
from src.tools import ToolRequest


class BuiltinToolTests(unittest.TestCase):
    def test_terminal_tool_executes_registered_request(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = TerminalTool(CommandRouter(TerminalExecutor(directory)))
            result = tool.execute(ToolRequest(
                action_id="A1",
                intent="run",
                payload={"argv": ["python", "-c", "print('hello')"]},
                expected_observation="hello",
            ))
            self.assertTrue(result.success)
            self.assertIn("hello", result.observation)
            self.assertTrue(result.evidence)

    def test_terminal_tool_rejects_malformed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = TerminalTool(CommandRouter(TerminalExecutor(directory)))
            result = tool.execute(ToolRequest("A1", "run", {"argv": "python"}, ""))
            self.assertFalse(result.success)
            self.assertEqual(result.observation, "INVALID_TERMINAL_PAYLOAD")


if __name__ == "__main__":
    unittest.main()
