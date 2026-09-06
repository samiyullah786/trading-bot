from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ContractRequirement:
    id: str
    statement: str
    mandatory: bool = True
    verification_hint: str = ""


class ContractAnalyzer:
    """Extract explicit completion obligations without pretending language parsing is proof."""

    _NEGATIVE = re.compile(r"\b(?:must not|mustn't|do not|don't|never)\b", re.I)
    _QUANTIFIER = re.compile(r"\b(?:all|every|each|at least|no more than|exactly|minimum|maximum)\b", re.I)

    def analyze(self, requirements: list[str]) -> list[ContractRequirement]:
        result: list[ContractRequirement] = []
        for raw in requirements:
            statement = " ".join(raw.split()).strip(" .;:")
            if not statement:
                continue
            hint_parts: list[str] = []
            if self._NEGATIVE.search(statement):
                hint_parts.append("negative constraint")
            if self._QUANTIFIER.search(statement):
                hint_parts.append("quantitative constraint")
            result.append(ContractRequirement(
                id=f"C{len(result) + 1}",
                statement=statement,
                mandatory=True,
                verification_hint=", ".join(hint_parts),
            ))
        return result

    def completeness_gaps(self, requirements: list[ContractRequirement]) -> list[str]:
        gaps: list[str] = []
        for item in requirements:
            if not item.verification_hint:
                gaps.append(item.id + ":verification-method-unspecified")
        return gaps
