from __future__ import annotations

from collections.abc import Callable

from .autonomy import ProposedAction
from .execution import TerminalExecutor
from .security import EvidenceSanitizer


class IndependentCommandVerifier:
    """Run a separate command to produce execution-independent evidence."""

    def __init__(self, terminal: TerminalExecutor):
        self.terminal = terminal
        self.sanitizer = EvidenceSanitizer(terminal.profile, terminal.redactor, terminal.secrets)

    def __call__(self, action: ProposedAction) -> tuple[bool, str]:
        command = getattr(action, "verification_command", None)
        if not command:
            return False, "NO_VERIFICATION_COMMAND"
        try:
            result = self.terminal.run(command)
        except Exception as exc:
            return False, self.sanitizer.sanitize(f"VERIFICATION_EXCEPTION={type(exc).__name__}")
        observation = self.sanitizer.sanitize(
            f"verification_returncode={result.returncode}; stdout={result.stdout}; stderr={result.stderr}"
        )
        return result.success, observation


class ActionExecutor:
    """Execute an action and require independent proof when configured."""

    def __init__(
        self,
        terminal: TerminalExecutor,
        verifier: Callable[[ProposedAction], tuple[bool, str]] | None = None,
        *,
        require_verification: bool = True,
    ):
        self.terminal = terminal
        self.verifier = verifier
        self.require_verification = require_verification
        self.sanitizer = EvidenceSanitizer(terminal.profile, terminal.redactor, terminal.secrets)

    def __call__(self, action: ProposedAction) -> tuple[bool, str, list[str]]:
        if not action.command:
            return False, "NO_EXECUTABLE_COMMAND", []
        try:
            result = self.terminal.run(action.command)
        except Exception as exc:
            return False, self.sanitizer.sanitize(f"EXECUTION_EXCEPTION={type(exc).__name__}"), []
        observation = self.sanitizer.sanitize(
            f"returncode={result.returncode}; stdout={result.stdout}; stderr={result.stderr}"
        )
        if not result.success:
            return False, observation, []

        if self.verifier is None:
            if self.require_verification:
                return False, f"{observation}; INDEPENDENT_VERIFICATION_REQUIRED", []
            return True, observation, [observation]

        try:
            verified, verification_observation = self.verifier(action)
        except Exception:
            return False, f"{observation}; VERIFICATION_EXCEPTION", []
        verification_observation = self.sanitizer.sanitize(verification_observation)
        observation = self.sanitizer.sanitize(f"{observation}; {verification_observation}")
        if not verified:
            return False, observation, []
        return True, observation, [verification_observation]
