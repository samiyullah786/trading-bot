from __future__ import annotations

from dataclasses import dataclass

from .provider import IntelligenceProvider, ReasoningRequest
from .metacognition import Metacognition
from .autonomy import ProposedAction


@dataclass
class ControllerDecision:
    actions: list[ProposedAction]
    confidence: float
    unknowns: list[str]
    requires_research: bool


class AgentController:
    """Turns structured reasoning into inspectable candidate actions."""

    def __init__(self, provider: IntelligenceProvider, metacognition: Metacognition | None = None):
        self.provider = provider
        self.metacognition = metacognition or Metacognition()

    def decide(self, objective: str, context: dict, constraints: list[str]) -> ControllerDecision:
        response = self.provider.reason(ReasoningRequest(objective, context, constraints))
        assessment = self.metacognition.assess(
            known=list(context.keys()),
            unknown=response.unknowns,
            confidence=response.confidence,
        )
        actions = []
        for item in response.actions:
            description = str(item.get("description", "")).strip()
            criteria = list(item.get("criterion_ids", []))
            command = item.get("command")
            verification_command = item.get("verification_command")
            tool_name = item.get("tool_name")
            tool_payload = item.get("tool_payload")
            depends_on = item.get("depends_on", [])
            if not isinstance(depends_on, list):
                depends_on = []
            try:
                expected_progress = float(item.get("expected_progress", 0.5))
                success_probability = float(item.get("success_probability", 0.5))
                cost = float(item.get("cost", 0.0))
                risk = float(item.get("risk", 0.0))
            except (TypeError, ValueError):
                expected_progress, success_probability, cost, risk = 0.5, 0.5, 0.0, 0.0
            if description and criteria:
                actions.append(ProposedAction(
                    description=description,
                    criterion_ids=criteria,
                    command=command,
                    verification_command=verification_command,
                    tool_name=str(tool_name) if tool_name else None,
                    tool_payload=dict(tool_payload) if isinstance(tool_payload, dict) else None,
                    depends_on=[str(value) for value in depends_on],
                    expected_progress=max(0.0, min(1.0, expected_progress)),
                    success_probability=max(0.0, min(1.0, success_probability)),
                    cost=max(0.0, cost),
                    risk=max(0.0, risk),
                    reversible=bool(item.get("reversible", True)),
                ))
        return ControllerDecision(
            actions=actions,
            confidence=assessment.confidence,
            unknowns=assessment.unknown,
            requires_research=self.metacognition.requires_research(assessment),
        )
