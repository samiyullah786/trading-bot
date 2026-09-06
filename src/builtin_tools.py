from __future__ import annotations

from .browser_cdp import ChromeDevTools, CdpTarget
from .command_router import CommandRouter, ShellCommand
from .tools import ToolRequest, ToolResult


class TerminalTool:
    name = "terminal"

    def __init__(self, router: CommandRouter):
        self.router = router

    def execute(self, request: ToolRequest) -> ToolResult:
        argv = request.payload.get("argv")
        shell = request.payload.get("shell", "native")
        if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
            return ToolResult(False, "INVALID_TERMINAL_PAYLOAD", [])
        try:
            result = self.router.run(ShellCommand(argv, shell))
        except Exception as exc:
            return ToolResult(False, f"terminal exception: {type(exc).__name__}: {exc}", [])
        observation = (
            f"returncode={result.returncode}; stdout={result.stdout[-2000:]}; "
            f"stderr={result.stderr[-2000:]}"
        )
        evidence = [observation] if result.success else []
        return ToolResult(result.success, observation, evidence, {"duration": result.duration, "truncated": result.truncated})


class BrowserTool:
    name = "browser"

    def __init__(self, browser: ChromeDevTools):
        self.browser = browser

    def _target(self, request: ToolRequest) -> CdpTarget:
        target_id = request.payload.get("target_id")
        targets = self.browser.targets()
        if target_id:
            for target in targets:
                if target.id == target_id:
                    return target
            raise ValueError("browser target not found")
        if not targets:
            raise RuntimeError("no browser page target available")
        return targets[0]

    def execute(self, request: ToolRequest) -> ToolResult:
        try:
            target = self._target(request)
            operation = request.intent.lower()
            if operation == "navigate":
                url = request.payload.get("url")
                if not isinstance(url, str):
                    raise ValueError("navigate requires url")
                result = self.browser.navigate(target, url)
                return ToolResult(True, f"navigated target={target.id} url={url}", [f"navigation result: {result}"], {"target_id": target.id})
            if operation == "evaluate":
                expression = request.payload.get("expression")
                if not isinstance(expression, str):
                    raise ValueError("evaluate requires expression")
                value = self.browser.evaluate(target, expression)
                observation = f"evaluation result: {value!r}"
                return ToolResult(True, observation, [observation], {"target_id": target.id})
            if operation == "screenshot":
                data = self.browser.screenshot_png(target)
                return ToolResult(True, f"captured screenshot ({len(data)} bytes)", [f"screenshot captured for target {target.id}"], {"target_id": target.id, "bytes": len(data), "png": data})
            return ToolResult(False, f"unsupported browser intent: {request.intent}", [])
        except Exception as exc:
            return ToolResult(False, f"browser exception: {type(exc).__name__}: {exc}", [])
