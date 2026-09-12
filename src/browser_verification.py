from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserVerification:
    ok: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]


class BrowserActionVerifier:
    """Evaluate explicit, bounded post-action expectations without trusting page instructions."""

    _ALLOWED = {"url_contains", "selector", "text_contains"}
    _MAX_VALUE = 4096

    @classmethod
    def validate(cls, expected: object) -> dict[str, str]:
        if expected is None:
            return {}
        if not isinstance(expected, dict):
            raise ValueError("browser verification must be an object")
        unknown = set(expected) - cls._ALLOWED
        if unknown:
            raise ValueError("unsupported browser verification field")
        result: dict[str, str] = {}
        for key in cls._ALLOWED:
            if key not in expected:
                continue
            value = expected[key]
            if not isinstance(value, str) or not value.strip() or len(value) > cls._MAX_VALUE:
                raise ValueError(f"invalid browser verification value: {key}")
            result[key] = value
        return result

    @classmethod
    def evaluate(cls, expected: dict[str, str], *, url: str = "", selector_found: bool | None = None, page_text: str = "") -> BrowserVerification:
        expected = cls.validate(expected)
        checks: list[str] = []
        failures: list[str] = []
        if "url_contains" in expected:
            checks.append("url_contains")
            if expected["url_contains"] not in url:
                failures.append("URL_MISMATCH")
        if "selector" in expected:
            checks.append("selector")
            if selector_found is not True:
                failures.append("SELECTOR_NOT_FOUND")
        if "text_contains" in expected:
            checks.append("text_contains")
            if expected["text_contains"] not in page_text:
                failures.append("TEXT_NOT_FOUND")
        return BrowserVerification(not failures, tuple(checks), tuple(failures))
