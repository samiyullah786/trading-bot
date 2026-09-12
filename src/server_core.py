from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .agent_controller import AgentController
from .server_protocol import ServerRequest, ServerResponse


class ServerCore:
    """OS-neutral authoritative AUREON brain boundary.

    UI clients are deliberately thin: Windows, Linux, macOS, Android and iOS
    communicate with this same contract. The core owns mission state and local
    reasoning; no hosted AI service is required.
    """

    def __init__(self, workspace: Path, controller: AgentController | None = None) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.controller = controller or AgentController()
        self._lock = threading.RLock()
        self._missions: dict[str, dict[str, Any]] = {}

    def handle(self, request: ServerRequest) -> ServerResponse:
        try:
            with self._lock:
                if request.operation == "health":
                    return ServerResponse(request.request_id, True, {"status": "ready", "protocol": request.protocol_version})
                if request.operation == "plan":
                    return self._plan(request)
                if request.operation == "mission.get":
                    mission_id = str(request.payload.get("mission_id", ""))
                    mission = self._missions.get(mission_id)
                    if mission is None:
                        return ServerResponse(request.request_id, False, error="mission not found")
                    return ServerResponse(request.request_id, True, mission)
                return ServerResponse(request.request_id, False, error="unsupported operation")
        except Exception as exc:
            return ServerResponse(request.request_id, False, error=f"{type(exc).__name__}: {exc}")

    def _plan(self, request: ServerRequest) -> ServerResponse:
        objective = str(request.payload.get("objective", "")).strip()
        if not objective:
            return ServerResponse(request.request_id, False, error="objective is required")
        decision = self.controller.decide(objective, {"workspace": str(self.workspace)}, [])
        mission_id = request.request_id
        mission = {
            "mission_id": mission_id,
            "objective": objective,
            "status": "planned" if decision.actions else "blocked",
            "confidence": decision.confidence,
            "analysis": decision.analysis,
            "unknowns": list(decision.unknowns),
            "actions": list(decision.actions),
        }
        self._missions[mission_id] = mission
        return ServerResponse(request.request_id, bool(decision.actions), mission, None if decision.actions else "no safe local plan")

    def snapshot(self) -> bytes:
        with self._lock:
            return json.dumps(self._missions, sort_keys=True, separators=(",", ":")).encode("utf-8")
