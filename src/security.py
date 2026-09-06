from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityProfile:
    timeout_seconds: float = 30.0
    max_output_bytes: int = 1_000_000
    allow_network: bool = False
    inherit_environment: bool = False
    allowed_executables: frozenset[str] | None = None


class EnvironmentFilter:
    """Minimizes credential leakage into child processes."""

    SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "API_KEY", "AUTH", "CREDENTIAL")

    @classmethod
    def is_sensitive(cls, key: str) -> bool:
        return any(marker in key.upper() for marker in cls.SENSITIVE_MARKERS)

    def __init__(self, profile: SecurityProfile):
        self.profile = profile

    def build(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        if self.profile.inherit_environment:
            result = dict(os.environ)
        else:
            result = {k: v for k, v in os.environ.items() if not self.is_sensitive(k)}
        if extra:
            result.update({k: v for k, v in extra.items() if not self.is_sensitive(k)})
        return result


class ExecutablePolicy:
    """Optional executable allow-list for high-assurance deployments."""

    def __init__(self, profile: SecurityProfile):
        self.profile = profile

    def validate(self, executable: str) -> None:
        allowed = self.profile.allowed_executables
        if allowed is not None and executable not in allowed:
            raise PermissionError(f"executable not allowed: {executable}")


class SecretRedactor:
    def redact(self, text: str, secrets: list[str]) -> str:
        output = text
        for secret in secrets:
            if secret:
                output = output.replace(secret, "[REDACTED]")
        return output
