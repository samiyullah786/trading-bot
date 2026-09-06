import unittest

from src.autonomy import ProposedAction
from src.tool_action_executor import ToolActionExecutor
from src.tools import Tool, ToolRegistry, ToolRequest, ToolResult


class EchoTool:
    name = "echo"

    def execute(self, request: ToolRequest) -> ToolResult:
        value = request.payload.get("value", "")
        return ToolResult(True, f"echo:{value}", [f"evidence:{value}"])


class ToolActionExecutorTests(unittest.TestCase):
    def test_selected_tool_executes_and_returns_evidence(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        executor = ToolActionExecutor(registry)
        result = executor(ProposedAction(
            "echo a value",
            ["R1"],
            tool_name="echo",
            tool_payload={"value": "hello"},
        ))
        self.assertEqual(result, (True, "echo:hello", ["evidence:hello"]))

    def test_missing_tool_selection_is_explicit(self):
        result = ToolActionExecutor(ToolRegistry())(ProposedAction("x", ["R1"]))
        self.assertEqual(result, (False, "NO_TOOL_SELECTED", []))


if __name__ == "__main__":
    unittest.main()
