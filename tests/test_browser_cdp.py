import unittest
from unittest.mock import Mock

from src.browser_cdp import ChromeDevTools
from src.browser_tool import BrowserTool
from src.tools import ToolRequest


class BrowserCdpTests(unittest.TestCase):
    def test_endpoint_validation(self):
        with self.assertRaises(ValueError):
            ChromeDevTools("not-a-url")

    def test_navigation_rejects_unsafe_scheme(self):
        client = ChromeDevTools()
        class Target:
            websocket_url = "ws://127.0.0.1:9222/devtools/page/x"
        with self.assertRaises(ValueError):
            client.navigate(Target(), "file:///etc/passwd")

    def test_navigation_requires_absolute_url(self):
        client = ChromeDevTools()
        class Target:
            websocket_url = "ws://127.0.0.1:9222/devtools/page/x"
        with self.assertRaises(ValueError):
            client.navigate(Target(), "/relative")

    def test_wait_for_polls_until_found(self):
        client = ChromeDevTools(timeout=1)
        target = object()
        client.evaluate = Mock(side_effect=[False, False, True])
        result = client.wait_for(target, "#ready", timeout=1, interval=0.05)
        self.assertEqual(result["found"], True)
        self.assertEqual(client.evaluate.call_count, 3)

    def test_fill_is_bounded(self):
        client = ChromeDevTools()
        with self.assertRaises(ValueError):
            client.fill(object(), "#x", "x" * 65537)

    def test_browser_tool_allowlist_blocks_untrusted_host(self):
        cdp = Mock()
        cdp.select_target.return_value = object()
        tool = BrowserTool(cdp, allowed_hosts={"example.com"})
        result = tool.execute(ToolRequest("a", "navigate", {"url": "https://evil.example/"}, ""))
        self.assertFalse(result.success)
        self.assertIn("not allowlisted", result.observation)
        cdp.navigate.assert_not_called()

    def test_browser_tool_allows_allowlisted_host(self):
        cdp = Mock()
        cdp.select_target.return_value = object()
        cdp.navigate.return_value = {"loaderId": "abc"}
        tool = BrowserTool(cdp, allowed_hosts={"example.com"})
        result = tool.execute(ToolRequest("a", "navigate", {"url": "https://example.com/"}, ""))
        self.assertTrue(result.success)
        cdp.navigate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
