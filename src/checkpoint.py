from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .domain import Action, Criterion, Mission, Observation, Status
from .persistence import JsonStore


CHECKPOINT_VERSION = 1


def mission_to_dict(mission: Mission) -> dict[str, Any]:
    """Serialize mission state using an explicit, versioned schema."""
    return {
        "schema_version": CHECKPOINT_VERSION,
        "mission": {
            "id": mission.id,
            "objective": mission.objective,
            "constraints": list(mission.constraints),
            "criteria": [asdict(item) | {"status": item.status.value} for item in mission.criteria],
            "observations": [asdict(item) for item in mission.observations],
            "actions": [asdict(item) | {"status": item.status.value} for item in mission.actions],
        },
    }


def mission_from_dict(data: dict[str, Any]) -> Mission:
    """Rehydrate a mission and reject unknown checkpoint schemas."""
    if data.get("schema_version") != CHECKPOINT_VERSION:
        raise ValueError("unsupported checkpoint schema version")
    raw = data.get("mission")
    if not isinstance(raw, dict):
        raise ValueError("checkpoint mission payload is invalid")

    criteria = [
        Criterion(
            id=item["id"],
            statement=item["statement"],
            mandatory=bool(item.get("mandatory", True)),
            status=Status(item.get("status", Status.PENDING.value)),
            evidence=list(item.get("evidence", [])),
        )
        for item in raw.get("criteria", [])
    ]
    observations = [Observation(**item) for item in raw.get("observations", [])]
    actions = [
        Action(
            id=item["id"],
            description=item["description"],
            criterion_ids=list(item.get("criterion_ids", [])),
            depends_on=list(item.get("depends_on", [])),
            status=Status(item.get("status", Status.PENDING.value)),
            attempts=int(item.get("attempts", 0)),
            fingerprints=list(item.get("fingerprints", [])),
            result=str(item.get("result", "")),
        )
        for item in raw.get("actions", [])
    ]
    return Mission(
        id=str(raw["id"]),
        objective=str(raw["objective"]),
        criteria=criteria,
        constraints=list(raw.get("constraints", [])),
        observations=observations,
        actions=actions,
    )


class CheckpointStore:
    """Persist and restore mission checkpoints through the atomic JsonStore."""

    def __init__(self, root: str):
        self.store = JsonStore(root)

    def save(self, mission: Mission) -> None:
        self.store.save(mission.id, mission_to_dict(mission))

    def load(self, mission_id: str) -> Mission | None:
        data = self.store.load(mission_id)
        return mission_from_dict(data) if data is not None else None

    def load_raw(self, mission_id: str) -> dict[str, Any] | None:
        return self.store.load(mission_id)
