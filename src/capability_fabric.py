from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import socket
import subprocess
import urllib.request
from urllib.parse import urlsplit

from .security import ExecutablePolicy, NetworkPolicy, SecurityProfile


@dataclass(frozen=True)
class CapabilityResult:
    success: bool
    value: object
    evidence: str


class _PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, fabric: "CapabilityFabric"):
        super().__init__()
        self.fabric = fabric

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.fabric.validate_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CapabilityFabric:
    """Provider-neutral bridge from agent intent to bounded machine capabilities."""

    def __init__(self, workspace: str | Path, max_read_bytes: int = 1_000_000,
                 security_profile: SecurityProfile | None = None,
                 allowed_http_hosts: set[str] | frozenset[str] | None = None):
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        self.max_read_bytes = max(1, min(max_read_bytes, 16_000_000))
        self.security_profile = security_profile or SecurityProfile()
        self.executable_policy = ExecutablePolicy(self.security_profile)
        self.network_policy = NetworkPolicy(self.security_profile, frozenset(allowed_http_hosts or ()))
        self._http_opener = urllib.request.build_opener(_PolicyRedirectHandler(self))

    def _path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError("path is required")
        candidate = (self.workspace / relative).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    def read_file(self, relative: str) -> CapabilityResult:
        path = self._path(relative)
        data = path.read_bytes()
        truncated = len(data) > self.max_read_bytes
        if truncated:
            data = data[:self.max_read_bytes]
        text = data.decode("utf-8", errors="replace")
        return CapabilityResult(True, text, f"read {len(data)} bytes from {path.relative_to(self.workspace)}" + (" (bounded)" if truncated else ""))

    def write_file(self, relative: str, content: str) -> CapabilityResult:
        if not isinstance(content, str):
            raise TypeError("content must be text")
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_read_bytes:
            raise ValueError("content exceeds bounded write size")
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        return CapabilityResult(True, len(encoded), f"wrote {len(encoded)} bytes to {path.relative_to(self.workspace)}")

    def list_directory(self, relative: str = ".", limit: int = 500) -> CapabilityResult:
        path = self._path(relative)
        if not path.is_dir():
            raise ValueError("not a directory")
        limit = max(1, min(limit, 5000))
        entries = sorted(p.name for p in path.iterdir())[:limit]
        return CapabilityResult(True, entries, f"listed {len(entries)} entries")

    def launch_application(self, executable: str, args: list[str] | None = None) -> CapabilityResult:
        if not executable or not isinstance(executable, str):
            raise ValueError("executable is required")
        self.executable_policy.validate(executable)
        argv = [executable] + list(args or [])
        if any(not isinstance(x, str) or not x for x in argv):
            raise ValueError("application arguments must be non-empty strings")
        process = subprocess.Popen(argv, cwd=self.workspace, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  shell=False, start_new_session=(os.name == "posix"))
        return CapabilityResult(True, process.pid, f"launched {executable} pid={process.pid}")

    def validate_http_url(self, url: str) -> str:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError("HTTP capability requires http(s) URL")
        parsed = urlsplit(url)
        host = parsed.hostname
        if not host:
            raise PermissionError("HTTP host is required")
        normalized = self.network_policy.validate_host(host)
        # Resolve names before connecting and reject every resolved address that is
        # private, local, reserved, or otherwise non-public to reduce DNS rebinding/SSRF risk.
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(normalized, parsed.port, type=socket.SOCK_STREAM)}
        except socket.gaierror as exc:
            raise PermissionError(f"HTTP host cannot be resolved: {normalized}") from exc
        if not addresses:
            raise PermissionError(f"HTTP host has no addresses: {normalized}")
        for address in addresses:
            self.network_policy.validate_host(address)
        return normalized

    def fetch_http(self, url: str, max_bytes: int = 1_000_000) -> CapabilityResult:
        self.validate_http_url(url)
        max_bytes = max(1, min(max_bytes, self.max_read_bytes))
        request = urllib.request.Request(url, headers={"User-Agent": "AutonomousAgent/1.0"})
        with self._http_opener.open(request, timeout=self.security_profile.timeout_seconds) as response:
            data = response.read(max_bytes + 1)
        truncated = len(data) > max_bytes
        data = data[:max_bytes]
        return CapabilityResult(True, data.decode("utf-8", errors="replace"), f"fetched {len(data)} bytes" + (" (bounded)" if truncated else ""))
