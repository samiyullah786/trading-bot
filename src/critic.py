from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Critique:
    claim: str
    risk: str
    challenge: str
    severity: str

class AdversarialCritic:
    def inspect(self, report: dict) -> list[Critique]:
        findings=[]
        for criterion in report.get("criteria", []):
            if criterion["status"] != "VERIFIED":
                findings.append(Critique(criterion["id"],"mandatory requirement remains unproven","obtain independent evidence","HIGH"))
            elif not criterion.get("evidence"):
                findings.append(Critique(criterion["id"],"verification lacks evidence","collect reproducible proof","CRITICAL"))
        return findings
