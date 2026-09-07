from __future__ import annotations

from .browser_cdp import ChromeDevTools
from .tools import ToolRequest, ToolResult


class BrowserTool:
    """Dependency-free browser tool with navigation, inspection and interaction."""

    name = "browser"

    def __init__(self, cdp: ChromeDevTools):
        self.cdp = cdp

    def execute(self, request: ToolRequest) -> ToolResult:
        operation = request.payload.get("operation", "navigate")
        try:
            target = self.cdp.select_target(request.payload.get("target_id"), request.payload.get("url_contains"))
            if operation == "navigate":
                result = self.cdp.navigate(target, request.payload["url"])
                return ToolResult(True, "navigation requested", [f"browser.loader_id={result.get('loaderId', '')}"], {"operation": operation})
            if operation == "evaluate":
                value = self.cdp.evaluate(target, request.payload["expression"])
                return ToolResult(True, "evaluation completed", [f"browser.value={str(value)[:8000]!r}"], {"operation": operation, "value": value})
            if operation == "click":
                value = self.cdp.click(target, request.payload["selector"])
                return ToolResult(True, "element clicked", [f"browser.click={value!r}"], {"operation": operation})
            if operation == "focus":
                self.cdp.focus(target, request.payload["selector"])
                return ToolResult(True, "element focused", ["browser.focus=ok"], {"operation": operation})
            if operation == "type":
                value = self.cdp.type_text(target, request.payload["text"])
                return ToolResult(True, "text inserted", [f"browser.type={value}"], {"operation": operation})
            if operation == "key":
                value = self.cdp.press_key(target, request.payload["key"])
                return ToolResult(True, "key dispatched", [f"browser.key={value}"], {"operation": operation})
            if operation == "read":
                value = self.cdp.page_text(target, int(request.payload.get("max_chars", 20000)))
                return ToolResult(True, "page text read", [f"browser.text={value[:12000]!r}"], {"operation": operation})
            if operation == "screenshot":
                data = self.cdp.screenshot_png(target)
                return ToolResult(True, f"screenshot captured ({len(data)} bytes)", [f"browser.screenshot_bytes={len(data)}"], {"operation": operation})
            return ToolResult(False, f"UNSUPPORTED_BROWSER_OPERATION:{operation}", [])
        except Exception as exc:
            return ToolResult(False, f"browser exception: {type(exc).__name__}: {exc}", [])
