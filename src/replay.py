from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .event_store import EventStore


@dataclass(frozen=True)
class ReplayAction:
    action_id: str
    description: str
    status: str
    criterion_ids: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    attempts: int = 0
    observation: str = ""
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReplayCriterion:
    criterion_id: str
    status: str = "PENDING"
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReplayState:
    mission_id: str | None
    last_cycle: int
    state: str
    actions: int
    observations: int
    action_states: dict[str, ReplayAction] = field(default_factory=dict)
    criteria: dict[str, ReplayCriterion] = field(default_factory=dict)


class EventReplayer:
    """Reconstruct operational mission state from the durable event stream."""

    def __init__(self, store: EventStore):
        self.store = store

    def replay(self) -> ReplayState:
        mission_id: str | None = None
        last_cycle = 0
        state = "UNKNOWN"
        observations = 0
        actions: dict[str, ReplayAction] = {}
        criteria: dict[str, ReplayCriterion] = {}

        for event in self.store.replay():
            payload = event.payload
            mission_id = self._mission_id(payload, mission_id)
            if event.event_type in {"agent_cycle", "agent.cycle"}:
                last_cycle = max(last_cycle, int(payload.get("cycle", 0)))
                state = str(payload.get("state", state))
                continue

            action_id = payload.get("action_id")
            if event.event_type == "action.created" and action_id:
                criterion_ids = tuple(str(x) for x in payload.get("criterion_ids", []))
                depends_on = tuple(str(x) for x in payload.get("depends_on", []))
                actions[str(action_id)] = ReplayAction(
                    str(action_id), str(payload.get("description", "")), "READY",
                    criterion_ids, depends_on,
                )
                for criterion_id in criterion_ids:
                    criteria.setdefault(criterion_id, ReplayCriterion(criterion_id))
            elif event.event_type == "action.started" and action_id:
                current = actions.get(str(action_id))
                if current:
                    actions[str(action_id)] = ReplayAction(
                        current.action_id, current.description, "RUNNING", current.criterion_ids,
                        current.depends_on, current.attempts + 1, current.observation, current.evidence,
                    )
            elif event.event_type in {"action.failed", "action.completed"} and action_id:
                current = actions.get(str(action_id))
                if current:
                    status = "VERIFIED" if event.event_type == "action.completed" else "FAILED"
                    actions[str(action_id)] = ReplayAction(
                        current.action_id, current.description, status, current.criterion_ids,
                        current.depends_on, current.attempts, str(payload.get("observation", current.observation)),
                        current.evidence,
                    )
            elif event.event_type in {"observation.created", "executor.observed"}:
                observations += 1
                if action_id and str(action_id) in actions:
                    current = actions[str(action_id)]
                    actions[str(action_id)] = ReplayAction(
                        current.action_id, current.description, current.status, current.criterion_ids,
                        current.depends_on, current.attempts, str(payload.get("observation", "")), current.evidence,
                    )
            elif event.event_type == "verification.completed":
                evidence = tuple(str(x) for x in payload.get("evidence", []))
                if action_id and str(action_id) in actions:
                    current = actions[str(action_id)]
                    actions[str(action_id)] = ReplayAction(
                        current.action_id, current.description, current.status, current.criterion_ids,
                        current.depends_on, current.attempts, current.observation, evidence,
                    )
                    for criterion_id in current.criterion_ids:
                        old = criteria.get(criterion_id, ReplayCriterion(criterion_id))
                        criteria[criterion_id] = ReplayCriterion(criterion_id, "VERIFIED", old.evidence + evidence)

        return ReplayState(mission_id, last_cycle, state, len(actions), observations, actions, criteria)

    @staticmethod
    def _mission_id(payload: dict[str, Any], current: str | None) -> str | None:
        value = payload.get("mission_id")
        return str(value) if value is not None else current

    def verify_and_replay(self) -> ReplayState:
        self.store.verify()
        return self.replay()
