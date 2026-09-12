import unittest

from src.tool_runtime import ToolRuntime, Verification
from src.tools import ToolRegistry, ToolRequest, ToolResult


class FakeTool:
    name = "fake"

    def __init__(self, results):
        self.results = iter(results)

    def execute(self, request):
        return next(self.results)


class ToolRuntimeTests(unittest.TestCase):
    def request(self):
        return ToolRequest("A1", "run", {}, "proof")

    def test_success_requires_evidence(self):
        registry = ToolRegistry()
        registry.register(FakeTool([ToolResult(True, "ok", ["proof"]) ]))
        result = ToolRuntime(registry).execute("fake", self.request())
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 1)
        self.assertIn("proof", result.evidence)

    def test_failure_retries_within_bound(self):
        registry = ToolRegistry()
        registry.register(FakeTool([ToolResult(False, "first", []), ToolResult(True, "second", ["proof"]) ]))
        result = ToolRuntime(registry, max_attempts=2).execute("fake", self.request())
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)

    def test_unknown_tool_fails_closed(self):
        result = ToolRuntime(ToolRegistry()).execute("missing", self.request())
        self.assertFalse(result.success)
        self.assertEqual(result.failure_class, "configuration")

    def test_verifier_can_reject_tool_success(self):
        registry = ToolRegistry()
        registry.register(FakeTool([ToolResult(True, "ok", ["weak"]) ]))
        def verifier(_, __):
            return Verification(False, (), "postcondition not proven")
        result = ToolRuntime(registry, verifier=verifier, max_attempts=1).execute("fake", self.request())
        self.assertFalse(result.success)
        self.assertEqual(result.failure_class, "verification_failure")


if __name__ == "__main__":
    unittest.main()
