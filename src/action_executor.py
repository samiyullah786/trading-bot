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
    """Bridge proposed actions to execution and optional independent verification."""

    def __init__(
        self,
        terminal: TerminalExecutor,
        verifier: Callable[[ProposedAction], tuple[bool, str]] | None = None,
    ):
        self.terminal = terminal
        self.verifier = verifier

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

        if self.verifier is not None:
            verified, verification_observation = self.verifier(action)
            observation = f"{observation}; {verification_observation}"
            if not verified:
                return False, observation, []
            return True, observation, [verification_observation]

        return True, observation, [observation]
