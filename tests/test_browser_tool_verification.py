import unittest

from src.browser_tool import BrowserTool
from src.browser_cdp import CdpTarget
from src.tools import ToolRequest


class FakeCdp:
    def __init__(self, *, url="https://example.test/done", selector=True, text="Completed"):
        self.target = CdpTarget("target-1", "ws://127.0.0.1:9222/devtools/page/1", "", url)
        self.selector = selector
        self.text = text

    def select_target(self, target_id=None, url_contains=None):
        if target_id and target_id != self.target.id:
            raise RuntimeError("target missing")
        if url_contains and url_contains not in self.target.url:
            raise RuntimeError("url target missing")
        return self.target

    def navigate(self, target, url):
        self.target.url = url
        return {"loaderId": "loader-1"}

    def click(self, target, selector):
        return {"clicked": selector}

    def fill(self, target, selector, text):
        return {"filled": selector, "valueLength": len(text)}

    def focus(self, target, selector):
        return True

    def evaluate(self, target, expression):
        return self.selector if "querySelector" in expression else True

    def page_text(self, target, max_chars=20000):
        return self.text[:max_chars]


class BrowserToolVerificationTests(unittest.TestCase):
    def test_navigation_can_require_post_action_verification(self):
        tool = BrowserTool(FakeCdp(), allowed_hosts={"example.test"})
        result = tool.execute(ToolRequest(
            "a1", "execute", {"operation": "navigate", "url": "https://example.test/done", "verify": {"url_contains": "/done", "text_contains": "Completed"}}, "verified",
        ))
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["verification"]["passed"], True)

    def test_failed_verification_is_not_reported_as_success(self):
        tool = BrowserTool(FakeCdp(url="https://example.test/error", text="Failed", selector=False), allowed_hosts={"example.test"})
        result = tool.execute(ToolRequest(
            "a2", "execute", {"operation": "click", "selector": "#submit", "verify": {"url_contains": "/done", "selector": "#success", "text_contains": "Completed"}}, "verified",
        ))
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["failure_class"], "verification")


if __name__ == "__main__":
    unittest.main()
