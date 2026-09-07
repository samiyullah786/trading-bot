from __future__ import annotations

from collections.abc import Callable

from .autonomy import ProposedAction
from .execution import TerminalExecutor


class IndependentCommandVerifier:
    """Run a separate command to produce execution-independent evidence."""

    def __init__(self, terminal: TerminalExecutor):
        self.terminal = terminal

    def __call__(self, action: ProposedAction) -> tuple[bool, str]:
        command = getattr(action, "verification_command", None)
        if not command:
            return False, "NO_VERIFICATION_COMMAND"
        result = self.terminal.run(command)
        observation = (
            f"verification_returncode={result.returncode}; "
            f"stdout={result.stdout[-2000:]}; stderr={result.stderr[-2000:]}"
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

    def __call__(self, action: ProposedAction) -> tuple[bool, str, list[str]]:
        if not action.command:
            return False, "NO_EXECUTABLE_COMMAND", []
        result = self.terminal.run(action.command)
        observation = (
            f"returncode={result.returncode}; stdout={result.stdout[-2000:]}; "
            f"stderr={result.stderr[-2000:]}"
        )
        if not result.success:
            return False, observation, []

        if self.verifier is None:
            if self.require_verification:
                return False, f"{observation}; INDEPENDENT_VERIFICATION_REQUIRED", []
            return True, observation, [observation]

        verified, verification_observation = self.verifier(action)
        observation = f"{observation}; {verification_observation}"
        if not verified:
            return False, observation, []
        return True, observation, [verification_observation]
