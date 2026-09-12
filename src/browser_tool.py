from __future__ import annotations

import ipaddress
import json
import socket
from urllib.parse import urlparse

from .browser_cdp import BrowserConnectionError, ChromeDevTools
from .browser_security import BrowserContentBoundary
from .browser_verification import BrowserActionVerifier
from .tools import ToolRequest, ToolResult


class BrowserTool:
    """Dependency-free browser tool with trust separation, verification and fail-closed recovery."""

    name = "browser"

    def __init__(self, cdp: ChromeDevTools, *, allowed_hosts: set[str] | None = None,
                 content_boundary: BrowserContentBoundary | None = None,
                 verifier: BrowserActionVerifier | None = None,
                 allow_private_hosts: bool = False):
        self.cdp = cdp
        self.allowed_hosts = {host.lower().rstrip(".") for host in (allowed_hosts or set())}
        self.content_boundary = content_boundary or BrowserContentBoundary()
        self.verifier = verifier or BrowserActionVerifier()
        self.allow_private_hosts = bool(allow_private_hosts)

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("browser navigation requires an absolute http(s) URL")
        if parsed.username or parsed.password:
            raise PermissionError("embedded URL credentials are not allowed")
        host = parsed.hostname.lower().rstrip(".")
        if self.allowed_hosts and host not in self.allowed_hosts:
            raise PermissionError("browser host is not allowlisted")
        if not self.allow_private_hosts:
            if host in {"localhost", "localhost.localdomain"}:
                raise PermissionError("private browser hosts are blocked")
            try:
                addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
            except socket.gaierror as exc:
                raise PermissionError("browser hostname could not be resolved safely") from exc
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                    raise PermissionError("private or special-use browser destination is blocked")

    def _content_result(self, value: object, operation: str) -> ToolResult:
        observation, evidence, metadata = self.content_boundary.package(value)
        metadata["operation"] = operation
        return ToolResult(True, observation, evidence, metadata)

    def _verify(self, target, expected: object, operation: str) -> ToolResult | None:
        checks = self.verifier.validate(expected)
        if not checks:
            return None
        fresh = self.cdp.select_target(target.id)
        selector_found = None
        if "selector" in checks:
            selector_found = bool(self.cdp.evaluate(fresh, "Boolean(document.querySelector(%s))" % json.dumps(checks["selector"])))
        page_text = self.cdp.page_text(fresh, 20000) if "text_contains" in checks else ""
        result = self.verifier.evaluate(checks, url=fresh.url, selector_found=selector_found, page_text=page_text)
        if result.ok:
            return ToolResult(True, "browser action verified", ["browser.verification=passed", *[f"browser.check={item}" for item in result.checks]], {"operation": operation, "verification": {"passed": True, "checks": list(result.checks)}})
        return ToolResult(False, "browser action verification failed: " + ",".join(result.failures), ["browser.verification=failed", *[f"browser.failure={item}" for item in result.failures]], {"operation": operation, "failure_class": "verification", "verification": {"passed": False, "checks": list(result.checks), "failures": list(result.failures)}})

    def _verified_action_result(self, target, operation: str, expected: object, evidence: list[str]) -> ToolResult:
        verification = self._verify(target, expected, operation)
        if verification is not None:
            if not verification.success:
                return verification
            return ToolResult(True, "browser action completed and verified", evidence + verification.evidence, {"operation": operation, "verification": verification.metadata.get("verification", {})})
        return ToolResult(True, f"browser {operation} completed", evidence, {"operation": operation})

    def _recover_target(self, target_id: str | None, url_contains: str | None) -> tuple[bool, str]:
        """Re-discover a browser target without replaying the interrupted action."""
        try:
            target = self.cdp.select_target(target_id, url_contains)
            return True, target.id
        except Exception as exc:
            return False, type(exc).__name__

    def execute(self, request: ToolRequest) -> ToolResult:
        operation = str(request.payload.get("operation", "navigate"))
        target_id = request.payload.get("target_id")
        url_contains = request.payload.get("url_contains")
        try:
            target = self.cdp.select_target(target_id, url_contains)
            expected = request.payload.get("verify")
            if operation == "navigate":
                url = str(request.payload["url"])
                self._check_url(url)
                result = self.cdp.navigate(target, url)
                return self._verified_action_result(target, operation, expected, [f"browser.loader_id={result.get('loaderId', '')}", f"browser.url={url}"])
            if operation == "evaluate":
                return self._content_result(self.cdp.evaluate(target, request.payload["expression"]), operation)
            if operation == "click":
                return self._verified_action_result(target, operation, expected, [f"browser.click={self.cdp.click(target, request.payload['selector'])!r}"])
            if operation == "focus":
                self.cdp.focus(target, request.payload["selector"])
                return self._verified_action_result(target, operation, expected, ["browser.focus=ok"])
            if operation == "fill":
                value = self.cdp.fill(target, request.payload["selector"], request.payload["text"])
                return self._verified_action_result(target, operation, expected, [f"browser.fill={value!r}"])
            if operation == "type":
                value = self.cdp.type_text(target, request.payload["text"])
                return ToolResult(True, "text inserted", [f"browser.type={value}"], {"operation": operation})
            if operation == "key":
                value = self.cdp.press_key(target, request.payload["key"])
                return ToolResult(True, "key dispatched", [f"browser.key={value}"], {"operation": operation})
            if operation == "scroll":
                value = self.cdp.scroll(target, request.payload.get("x", 0), request.payload.get("y", 600))
                return ToolResult(True, "page scrolled", [f"browser.scroll={value!r}"], {"operation": operation})
            if operation == "wait_for":
                value = self.cdp.wait_for(target, request.payload["selector"], request.payload.get("timeout"))
                return ToolResult(True, "element appeared", [f"browser.wait={value!r}"], {"operation": operation})
            if operation == "dom":
                return self._content_result(self.cdp.dom_snapshot(target, int(request.payload.get("max_chars", 50000))), operation)
            if operation == "accessibility":
                return self._content_result(self.cdp.accessibility_snapshot(target, int(request.payload.get("max_chars", 50000))), operation)
            if operation == "back":
                self.cdp.back(target)
                return self._verified_action_result(target, operation, expected, ["browser.history=back"])
            if operation == "forward":
                self.cdp.forward(target)
                return self._verified_action_result(target, operation, expected, ["browser.history=forward"])
            if operation == "reload":
                self.cdp.reload(target)
                return self._verified_action_result(target, operation, expected, ["browser.reload=ok"])
            if operation == "read":
                return self._content_result(self.cdp.page_text(target, int(request.payload.get("max_chars", 20000))), operation)
            if operation == "screenshot":
                data = self.cdp.screenshot_png(target)
                return ToolResult(True, f"screenshot captured ({len(data)} bytes)", [f"browser.screenshot_bytes={len(data)}"], {"operation": operation, "trust_boundary": "browser_binary"})
            return ToolResult(False, f"UNSUPPORTED_BROWSER_OPERATION:{operation}", [], {"operation": operation, "failure_class": "configuration"})
        except PermissionError as exc:
            return ToolResult(False, f"browser policy: {exc}", [], {"operation": operation, "failure_class": "configuration"})
        except BrowserConnectionError as exc:
            recovered, recovered_target = self._recover_target(target_id, url_contains)
            metadata = {"operation": operation, "failure_class": "execution", "browser_connection": {"reconnect_attempted": True, "recovered": recovered, "target_id": recovered_target if recovered else None}, "action_replay": "forbidden_after_transport_uncertainty"}
            return ToolResult(False, f"browser transport lost; action not replayed: {exc}", ["browser.reconnect_attempted=true", f"browser.recovered={str(recovered).lower()}"], metadata)
        except Exception as exc:
            return ToolResult(False, f"browser exception: {type(exc).__name__}: {exc}", [], {"operation": operation, "failure_class": "execution"})
