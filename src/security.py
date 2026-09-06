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

    def __init__(self, profile: SecurityProfile):
        self.profile = profile

    def build(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        if self.profile.inherit_environment:
            result = dict(os.environ)
        else:
            result = {k: v for k, v in os.environ.items() if not any(marker in k.upper() for marker in self.SENSITIVE_MARKERS)}
        if extra:
            result.update(extra)
        return result

class SecretRedactor:
    def redact(self, text: str, secrets: list[str]) -> str:
        output = text
        for secret in secrets:
            if secret:
                output = output.replace(secret, "[REDACTED]")
        return output
