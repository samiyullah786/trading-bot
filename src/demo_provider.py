from __future__ import annotations
from .provider import ReasoningRequest, ReasoningResponse

class DeterministicMissionProvider:
    """Test/demo provider that emits only explicitly configured executable plans."""

    def __init__(self, actions_by_criterion: dict[str, list[str]]):
        self.actions_by_criterion = actions_by_criterion

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        actions = []
        for criterion in request.context.get("criteria", []):
            criterion_id = criterion["id"]
            command = self.actions_by_criterion.get(criterion_id)
            if command:
                actions.append({
                    "description": f"Execute verification action for {criterion_id}",
                    "criterion_ids": [criterion_id],
                    "command": command,
                })
        return ReasoningResponse("deterministic executable plan", actions, 1.0, [])
