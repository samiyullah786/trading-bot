from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .autonomy import AutonomousLoop
from .ledger import Ledger


@dataclass
class RuntimeEvent:
    cycle: int
    state: str
    detail: str


class Runtime:
    """Orchestration shell that can resume from a previously consumed cycle budget."""

    def __init__(self, loop: AutonomousLoop, ledger: Ledger | None = None):
        self.loop = loop
        self.ledger = ledger or Ledger()

    def _completed_cycles(self) -> int:
        return sum(1 for entry in self.ledger.entries if entry.category == "cycle")

    def run(self, maximum_cycles: int = 100) -> dict[str, Any]:
        events: list[RuntimeEvent] = []
        start = self._completed_cycles() + 1
        for cycle in range(start, maximum_cycles + 1):
            result = self.loop.cycle()
            state = result["state"]
            detail = result.get("description") or result.get("reason") or result.get("action", "")
            event = RuntimeEvent(cycle, state, str(detail))
            events.append(event)
            self.ledger.append("cycle", state, cycle=cycle, result=result)

            if state == "COMPLETE":
                return {"state": "COMPLETE", "events": events, "report": result["report"]}
            if state == "BLOCKED":
                return {"state": "BLOCKED", "events": events, "result": result}

        return {
            "state": "PAUSED",
            "reason": "cycle budget reached without completion",
            "events": events,
            "report": self.loop.kernel.report(),
        }
