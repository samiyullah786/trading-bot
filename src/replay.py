from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .event_store import EventStore, Event


@dataclass(frozen=True)
class ReplayState:
    mission_id: str | None
    last_cycle: int
    state: str
    actions: int
    observations: int


class EventReplayer:
    """Reconstruct the runtime's minimal operational state from durable events."""

    def __init__(self, store: EventStore):
        self.store = store

    def replay(self) -> ReplayState:
        mission_id: str | None = None
        last_cycle = 0
        state = "UNKNOWN"
        actions = 0
        observations = 0
        for event in self.store.replay():
            mission_id = self._mission_id(event.payload, mission_id)
            if event.event_type in {"agent_cycle", "agent.cycle"}:
                last_cycle = max(last_cycle, int(event.payload.get("cycle", 0)))
                state = str(event.payload.get("state", state))
            elif event.event_type in {"action.created", "action.started", "action.failed", "action.completed"}:
                actions += 1 if event.event_type == "action.created" else 0
            elif event.event_type in {"observation.created", "executor.observed"}:
                observations += 1
        return ReplayState(mission_id, last_cycle, state, actions, observations)

    @staticmethod
    def _mission_id(payload: dict[str, Any], current: str | None) -> str | None:
        value = payload.get("mission_id")
        return str(value) if value is not None else current

    def verify_and_replay(self) -> ReplayState:
        self.store.verify()
        return self.replay()
