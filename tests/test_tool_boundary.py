import tempfile
import unittest
from pathlib import Path

from src.browser_tool import BrowserTool
from src.execution import TerminalExecutor
from src.policy import ExecutionPolicy
from src.terminal_tool import TerminalTool
from src.tool_action_executor import ToolActionExecutor
from src.tools import ToolRegistry


class ToolBoundaryTests(unittest.TestCase):
    def test_terminal_tool_executes_registered_command(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = ToolRegistry()
            registry.register(TerminalTool(TerminalExecutor(directory)))
            result = registry.execute("terminal", __import__("src.tools", fromlist=["ToolRequest"]).ToolRequest(
                "a1", "write", {"command": ["python", "-c", "print('ok')"]}, "ok"
            ))
            self.assertTrue(result.success)
            self.assertIn("ok", result.observation)

    def test_tool_action_executor_blocks_high_risk(self):
        registry = ToolRegistry()
        executor = ToolActionExecutor(registry, ExecutionPolicy())
        from src.autonomy import ProposedAction
        result = executor(ProposedAction("danger", ["c1"], tool_name="missing", risk="HIGH"))
        self.assertFalse(result[0])
        self.assertIn("POLICY_BLOCKED", result[1])

    def test_browser_tool_requires_supported_operation(self):
        class FakeCdp:
            def select_target(self, *args):
                return object()
        result = BrowserTool(FakeCdp()).execute(__import__("src.tools", fromlist=["ToolRequest"]).ToolRequest(
            "a1", "browser", {"operation": "unknown"}, ""
        ))
        self.assertFalse(result.success)
        self.assertIn("UNSUPPORTED_BROWSER_OPERATION", result.observation)


if __name__ == "__main__":
    unittest.main()
