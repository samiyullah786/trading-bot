from __future__ import annotations

from .browser_cdp import ChromeDevTools
from .tools import ToolRequest, ToolResult


class BrowserTool:
    """ToolRegistry adapter exposing bounded browser operations through CDP."""

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
                return ToolResult(True, "evaluation completed", [f"browser.value={value!r}"], {"operation": operation, "value": value})
            if operation == "screenshot":
                data = self.cdp.screenshot_png(target)
                return ToolResult(True, f"screenshot captured ({len(data)} bytes)", [f"browser.screenshot_bytes={len(data)}"], {"operation": operation})
            return ToolResult(False, f"UNSUPPORTED_BROWSER_OPERATION:{operation}", [])
        except Exception as exc:
            return ToolResult(False, f"browser exception: {type(exc).__name__}: {exc}", [])
