from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class SecurityProfile:
    timeout_seconds: float = 30.0
    max_output_bytes: int = 1_000_000
    allow_network: bool = False
    inherit_environment: bool = False

class EnvironmentFilter:
    """Minimizes credential leakage into child processes."""
    SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "API_KEY", "AUTH")

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

class SecretRedactor:
    def redact(self, text: str, secrets: list[str]) -> str:
        output = text
        for secret in secrets:
            if secret:
                output = output.replace(secret, "[REDACTED]")
        return output
