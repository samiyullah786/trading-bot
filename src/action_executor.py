from __future__ import annotations

from .autonomy import ProposedAction
from .execution import TerminalExecutor

class ActionExecutor:
    """Bridges proposed actions to concrete execution boundaries."""

    def __init__(self, terminal: TerminalExecutor):
        self.terminal = terminal

    def __call__(self, action: ProposedAction) -> tuple[bool, str, list[str]]:
        if not action.command:
            return False, "NO_EXECUTABLE_COMMAND", []

        result = self.terminal.run(action.command)
        observation = (
            f"returncode={result.returncode}; stdout={result.stdout[-2000:]}; "
            f"stderr={result.stderr[-2000:]}"
        )
        evidence = [observation] if result.success else []
        return result.success, observation, evidence
