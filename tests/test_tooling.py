import unittest
from src.tooling import ToolRouter, ToolCall, ToolOutcome

class ToolingTests(unittest.TestCase):
    def test_registered_tool_executes(self):
        router = ToolRouter()
        router.register("echo", lambda p: ToolOutcome(True, p["text"], [p["text"]]))
        outcome = router.execute(ToolCall("echo", {"text": "hello"}))
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.observation, "hello")

    def test_unknown_tool_fails_explicitly(self):
        outcome = ToolRouter().execute(ToolCall("missing"))
        self.assertFalse(outcome.success)

if __name__ == "__main__":
    unittest.main()
