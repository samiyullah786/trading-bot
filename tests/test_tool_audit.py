import unittest

from src.ledger import Ledger
from src.tools import ToolRegistry, ToolRequest, ToolResult


class EchoTool:
    name = "echo"

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(True, "ok", ["verified:ok"], {"kind": "test"})


class ToolAuditTests(unittest.TestCase):
    def test_tool_lifecycle_is_recorded_with_action_identity(self):
        ledger = Ledger()
        registry = ToolRegistry(audit=ledger)
        registry.register(EchoTool())

        result = registry.execute(
            "echo",
            ToolRequest("A17", "echo test", {"x": 1}, "ok", "LOW"),
        )

        self.assertTrue(result.success)
        self.assertEqual([entry.kind for entry in ledger.entries], ["tool.started", "tool.completed"])
        self.assertEqual(ledger.entries[0].data["action_id"], "A17")
        self.assertEqual(ledger.entries[1].data["tool"], "echo")
        self.assertEqual(ledger.entries[1].data["evidence"], ["verified:ok"])

    def test_invalid_request_is_rejected_before_tool_execution(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        with self.assertRaises(ValueError):
            registry.execute("echo", ToolRequest("", "test", {}, "ok"))


if __name__ == "__main__":
    unittest.main()
