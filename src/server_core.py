from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, is_dataclass
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

    STATE_FILE = ".aureon-missions.json"

    def __init__(self, workspace: Path, controller: AgentController | None = None) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.controller = controller or AgentController()
        self._state_path = self.workspace / self.STATE_FILE
        self._lock = threading.RLock()
        self._missions: dict[str, dict[str, Any]] = {}
        self._load_state()

    def handle(self, request: ServerRequest) -> ServerResponse:
        try:
            with self._lock:
                if request.operation == "health":
                    return ServerResponse(request.request_id, True, {"status": "ready", "protocol": request.protocol_version})
                if request.operation in {"plan", "mission.create"}:
                    return self._plan(request)
                if request.operation in {"mission.get", "mission.status"}:
                    return self._get(request)
                if request.operation == "mission.resume":
                    return self._resume(request)
                if request.operation == "mission.cancel":
                    return self._cancel(request)
                if request.operation == "mission.step":
                    return self._step(request)
                return ServerResponse(request.request_id, False, error="unsupported operation")
        except Exception as exc:
            return ServerResponse(request.request_id, False, error=f"INTERNAL_ERROR:{type(exc).__name__}")

    def _plan(self, request: ServerRequest) -> ServerResponse:
        objective = str(request.payload.get("objective", "")).strip()
        if not objective:
            return ServerResponse(request.request_id, False, error="OBJECTIVE_REQUIRED")
        decision = self.controller.decide(objective, {"workspace": str(self.workspace)}, [])
        mission_id = str(request.payload.get("mission_id", request.request_id)).strip() or request.request_id
        mission = {
            "mission_id": mission_id,
            "objective": objective,
            "status": "planned" if decision.actions else "blocked",
            "confidence": decision.confidence,
            "analysis": decision.analysis,
            "unknowns": list(decision.unknowns),
            "actions": [self._json_safe(action) for action in decision.actions],
            "next_action": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._missions[mission_id] = mission
        self._persist_state()
        return ServerResponse(request.request_id, bool(decision.actions), mission, None if decision.actions else "NO_SAFE_LOCAL_PLAN")

    def _get(self, request: ServerRequest) -> ServerResponse:
        mission_id = str(request.payload.get("mission_id", "")).strip()
        if not mission_id:
            return ServerResponse(request.request_id, False, error="MISSION_ID_REQUIRED")
        mission = self._missions.get(mission_id)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        return ServerResponse(request.request_id, True, dict(mission))

    def _resume(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] in {"completed", "cancelled"}:
            return ServerResponse(request.request_id, False, error="MISSION_TERMINAL")
        if not mission["actions"]:
            mission["status"] = "blocked"
        else:
            mission["status"] = "ready"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, True, dict(mission))

    def _cancel(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] == "completed":
            return ServerResponse(request.request_id, False, error="MISSION_ALREADY_COMPLETED")
        mission["status"] = "cancelled"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, True, dict(mission))

    def _step(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] in {"cancelled", "completed", "blocked"}:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_RUNNABLE")
        index = int(mission["next_action"])
        actions = mission["actions"]
        if index >= len(actions):
            mission["status"] = "completed"
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, True, dict(mission))
        mission["status"] = "executing"
        mission["current_action"] = actions[index]
        mission["next_action"] = index + 1
        mission["updated_at"] = time.time()
        if mission["next_action"] >= len(actions):
            mission["status"] = "awaiting_execution"
        self._persist_state()
        return ServerResponse(request.request_id, True, dict(mission))

    def _mission(self, request: ServerRequest) -> dict[str, Any] | None:
        mission_id = str(request.payload.get("mission_id", "")).strip()
        return self._missions.get(mission_id) if mission_id else None

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if is_dataclass(value):
            return {key: ServerCore._json_safe(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {str(key): ServerCore._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [ServerCore._json_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return
        try:
            raw = self._state_path.read_bytes()
            if len(raw) > 10_000_000:
                raise ValueError("state exceeds limit")
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("state must be an object")
            self._missions = {str(k): v for k, v in value.items() if isinstance(v, dict)}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            # Fail closed: corrupted state is not silently used as live state.
            self._missions = {}

    def _persist_state(self) -> None:
        payload = json.dumps(self._missions, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(payload) > 10_000_000:
            raise ValueError("mission state exceeds limit")
        temporary = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, self._state_path)

    def snapshot(self) -> bytes:
        with self._lock:
            return json.dumps(self._missions, sort_keys=True, separators=(",", ":")).encode("utf-8")
