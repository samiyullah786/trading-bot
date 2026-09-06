from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from .autonomy import AutonomousLoop, ProposedAction, Strategist
from .kernel import OutcomeKernel
from .ledger import Ledger
from .quality import QualityController, QualityGate

@dataclass
class RuntimeEvent:
    cycle: int
    state: str
    detail: str

class Runtime:
    """Durable orchestration shell around the autonomous loop."""

    def __init__(self, loop: AutonomousLoop, ledger: Ledger | None = None):
        self.loop = loop
        self.ledger = ledger or Ledger()

    def run(self, maximum_cycles: int = 100) -> dict:
        events: list[RuntimeEvent] = []
        for cycle in range(1, maximum_cycles + 1):
            result = self.loop.cycle()
            state = result["state"]
            detail = result.get("description") or result.get("reason") or result.get("action", "")
            events.append(RuntimeEvent(cycle, state, str(detail)))
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
