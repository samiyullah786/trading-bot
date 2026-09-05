from __future__ import annotations

import re
from .domain import Mission, Criterion

class MissionCompiler:
    """Turns a structured objective into explicit truth conditions.

    This deliberately does not let an LLM silently redefine success. Any
    intelligence provider may propose criteria, but the compiled contract
    remains inspectable and user-owned.
    """

    def compile(self, objective: str, requirements: list[str] | None = None) -> Mission:
        requirements = requirements or []
        criteria = []
        for index, statement in enumerate(requirements, start=1):
            clean = statement.strip()
            if clean:
                criteria.append(Criterion(f"R{index}", clean))

        if not criteria:
            clauses = [
                x.strip(" .")
                for x in re.split(r"\b(?:and|then|,|;)\b", objective)
                if len(x.strip()) > 3
            ]
            criteria = [
                Criterion(f"R{index}", clause)
                for index, clause in enumerate(clauses, start=1)
            ] or [Criterion("R1", objective)]

        return Mission.create(objective, criteria)
