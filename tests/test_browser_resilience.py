import unittest

from src.browser_cdp import BrowserConnectionError, CdpTarget
from src.browser_tool import BrowserTool
from src.tools import ToolRequest


class DeadCdp:
    def select_target(self, target_id=None, url_contains=None):
        if target_id == "tab-1":
            return CdpTarget("tab-1", "ws://127.0.0.1:9222/devtools/page/tab-1", url="https://example.com")
        raise BrowserConnectionError("browser unavailable")

    def click(self, target, selector):
        raise BrowserConnectionError("socket disappeared")


class BrowserResilienceTests(unittest.TestCase):
    def test_transport_failure_reconnects_without_replaying_action(self):
        tool = BrowserTool(DeadCdp(), allowed_hosts={"example.com"})
        request = ToolRequest("a1", "click", {"operation": "click", "target_id": "tab-1", "selector": "#pay"}, "")
        result = tool.execute(request)
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["action_replay"], "forbidden_after_transport_uncertainty")
        self.assertTrue(result.metadata["browser_connection"]["recovered"])

    def test_embedded_credentials_are_blocked(self):
        class Cdp:
            def select_target(self, *args, **kwargs):
                return CdpTarget("tab", "ws://127.0.0.1:9222/x", url="about:blank")
            def navigate(self, *args, **kwargs):
                raise AssertionError("navigation must be rejected before CDP action")

        tool = BrowserTool(Cdp(), allowed_hosts={"example.com"})
        request = ToolRequest("a2", "navigate", {"operation": "navigate", "url": "https://user:pass@example.com/"}, "")
        result = tool.execute(request)
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["failure_class"], "configuration")


if __name__ == "__main__":
    unittest.main()
