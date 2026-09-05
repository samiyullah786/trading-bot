from __future__ import annotations

from .domain import Mission, Status, Observation

class OutcomeKernel:
    """Custom mission-control kernel.

    The kernel owns truth conditions. Intelligence providers may propose
    actions, but they cannot directly declare a mission complete.
    """

    def __init__(self, mission: Mission):
        self.mission = mission

    def observe(self, source: str, fact: str) -> None:
        self.mission.observations.append(Observation(source=source, fact=fact))

    def criterion(self, criterion_id: str):
        for item in self.mission.criteria:
            if item.id == criterion_id:
                return item
        raise KeyError(criterion_id)

    def add_evidence(self, criterion_id: str, evidence: str) -> None:
        item = self.criterion(criterion_id)
        if evidence not in item.evidence:
            item.evidence.append(evidence)

    def gaps(self) -> list[str]:
        return [
            item.id for item in self.mission.criteria
            if item.mandatory and item.status != Status.VERIFIED
        ]

    def verify(self) -> bool:
        for item in self.mission.criteria:
            if item.mandatory:
                item.status = Status.VERIFIED if item.evidence else Status.PENDING
        return not self.gaps()

    def ready_actions(self):
        verified = {a.id for a in self.mission.actions if a.status == Status.VERIFIED}
        return [
            a for a in self.mission.actions
            if a.status in (Status.PENDING, Status.READY)
            and all(dep in verified for dep in a.depends_on)
        ]

    def report(self) -> dict:
        complete = self.verify()
        return {
            "mission": self.mission.id,
            "objective": self.mission.objective,
            "complete": complete,
            "open_gaps": self.gaps(),
            "criteria": [
                {
                    "id": c.id,
                    "status": c.status.value,
                    "evidence": c.evidence,
                }
                for c in self.mission.criteria
            ],
        }
