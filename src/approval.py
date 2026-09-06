from __future__ import annotations

from dataclasses import dataclass

@dataclass
class ApprovalRequest:
    action: str
    reason: str
    risk: str

class ApprovalGate:
    """Explicit boundary for actions requiring human authorization."""

    def __init__(self):
        self.pending: list[ApprovalRequest] = []

    def request(self, action: str, reason: str, risk: str) -> ApprovalRequest:
        request = ApprovalRequest(action, reason, risk)
        self.pending.append(request)
        return request

    def approve(self, request: ApprovalRequest) -> bool:
        if request not in self.pending:
            return False
        self.pending.remove(request)
        return True
