from __future__ import annotations

import json
from pathlib import Path
from .domain import Mission, Criterion, Observation, Action, Status

def save(mission: Mission, path: str) -> None:
    payload = {
        "id": mission.id,
        "objective": mission.objective,
        "constraints": mission.constraints,
        "criteria": [
            {
                "id": c.id,
                "statement": c.statement,
                "mandatory": c.mandatory,
                "status": c.status.value,
                "evidence": c.evidence,
            } for c in mission.criteria
        ],
        "observations": [
            {"source": o.source, "fact": o.fact, "timestamp": o.timestamp}
            for o in mission.observations
        ],
        "actions": [
            {
                "id": a.id,
                "description": a.description,
                "criterion_ids": a.criterion_ids,
                "depends_on": a.depends_on,
                "status": a.status.value,
                "attempts": a.attempts,
                "fingerprints": a.fingerprints,
                "result": a.result,
            } for a in mission.actions
        ],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2))

def load(path: str) -> Mission:
    raw = json.loads(Path(path).read_text())
    return Mission(
        id=raw["id"],
        objective=raw["objective"],
        constraints=raw.get("constraints", []),
        criteria=[
            Criterion(
                id=c["id"],
                statement=c["statement"],
                mandatory=c.get("mandatory", True),
                status=Status(c.get("status", "PENDING")),
                evidence=c.get("evidence", []),
            ) for c in raw["criteria"]
        ],
        observations=[Observation(**o) for o in raw.get("observations", [])],
        actions=[
            Action(
                id=a["id"],
                description=a["description"],
                criterion_ids=a["criterion_ids"],
                depends_on=a.get("depends_on", []),
                status=Status(a.get("status", "PENDING")),
                attempts=a.get("attempts", 0),
                fingerprints=a.get("fingerprints", []),
                result=a.get("result", ""),
            ) for a in raw.get("actions", [])
        ],
    )
