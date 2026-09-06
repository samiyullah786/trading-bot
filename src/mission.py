from __future__ import annotations

import re
from .domain import Mission, Criterion


class MissionCompiler:
    """Compile human objectives into explicit, inspectable truth conditions.

    The compiler is intentionally conservative: explicit requirements are never
    rewritten, while implicit objectives are split only at high-confidence
    structural boundaries. The resulting contract is still verified by the
    kernel rather than trusted merely because it was parsed successfully.
    """

    _BULLET = re.compile(r"(?:^|\n)\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+")
    _CLAUSE = re.compile(r"\s*(?:;|\n+|\bthen\b|\band\b)\s*", re.IGNORECASE)

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip(" \t\r\n.;:")
        return text

    def _split_requirement_block(self, text: str) -> list[str]:
        """Split bullets/numbered lists without destroying ordinary sentences."""
        if self._BULLET.search(text):
            parts = self._BULLET.split(text)
            return [self._clean(part) for part in parts if self._clean(part)]
        return [self._clean(text)] if self._clean(text) else []

    def _implicit_clauses(self, objective: str) -> list[str]:
        normalized = objective.replace("\r\n", "\n").strip()
        clauses: list[str] = []
        for block in normalized.split("\n"):
            block = self._clean(block)
            if not block:
                continue
            pieces = self._CLAUSE.split(block)
            clauses.extend(piece for piece in pieces if len(piece) >= 4)
        return clauses or [self._clean(objective)]

    def compile(self, objective: str, requirements: list[str] | None = None) -> Mission:
        objective = self._clean(objective)
        if not objective:
            raise ValueError("objective must not be empty")

        criteria: list[Criterion] = []
        explicit = requirements or []
        for statement in explicit:
            for clean in self._split_requirement_block(statement):
                criteria.append(Criterion(f"R{len(criteria) + 1}", clean))

        if not criteria:
            criteria = [
                Criterion(f"R{index}", clause)
                for index, clause in enumerate(self._implicit_clauses(objective), start=1)
                if clause
            ]

        if not criteria:
            criteria = [Criterion("R1", objective)]
        return Mission.create(objective, criteria)
