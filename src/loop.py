from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class LoopDecision:
    state: str
    reason: str
    cycle: int

class MissionRunner:
    """Long-running orchestration shell.

    The runner never interprets PAUSED/BLOCKED as success. A cycle budget is
    only a resource boundary; callers can persist state and resume later.
    """

    def __init__(self, cycle: Callable[[], dict]):
        self.cycle = cycle

    def run(self, max_cycles: int = 1000) -> list[LoopDecision]:
        if max_cycles < 1:
            raise ValueError("max_cycles must be positive")
        history: list[LoopDecision] = []
        for number in range(1, max_cycles + 1):
            result = self.cycle()
            state = result.get("state", "UNKNOWN")
            decision = LoopDecision(state, result.get("reason", ""), number)
            history.append(decision)
            if state == "COMPLETE":
                return history
            if state == "BLOCKED":
                return history
        return history
