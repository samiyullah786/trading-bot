from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .action_executor import ActionExecutor, IndependentCommandVerifier
from .agent_controller import AgentController
from .autonomy import ProposedAction
from .execution import TerminalExecutor
from .server_protocol import ServerRequest, ServerResponse


class ServerCore:
    """OS-neutral authoritative AUREON brain boundary.

    Clients remain thin interfaces. Mission planning and execution happen in
    this server-side core using the repository's existing safety and evidence
    boundaries. A mission is never marked complete merely because an action was
    attempted: executable actions require independent verification.
    """

    STATE_FILE = ".aureon-missions.json"
    MAX_ACTIONS = 128
    MAX_HISTORY = 256
    MAX_RUN_STEPS = 32

    def __init__(self, workspace: Path, controller: AgentController | None = None) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.controller = controller or AgentController()
        self._state_path = self.workspace / self.STATE_FILE
        self._lock = threading.RLock()
        self._missions: dict[str, dict[str, Any]] = {}
        self._terminal = TerminalExecutor(self.workspace)
        self._executor = ActionExecutor(self._terminal, IndependentCommandVerifier(self._terminal))
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
                if request.operation == "mission.run":
                    return self._run(request)
                return ServerResponse(request.request_id, False, error="UNSUPPORTED_OPERATION")
        except Exception as exc:
            return ServerResponse(request.request_id, False, error=f"INTERNAL_ERROR:{type(exc).__name__}")

    def _plan(self, request: ServerRequest) -> ServerResponse:
        objective = str(request.payload.get("objective", "")).strip()
        if not objective:
            return ServerResponse(request.request_id, False, error="OBJECTIVE_REQUIRED")
        decision = self.controller.decide(objective, {"workspace": str(self.workspace)}, [])
        actions = [self._json_safe(action) for action in decision.actions]
        if len(actions) > self.MAX_ACTIONS:
            return ServerResponse(request.request_id, False, error="PLAN_TOO_LARGE")
        mission_id = str(request.payload.get("mission_id", request.request_id)).strip() or request.request_id
        if mission_id in self._missions:
            return ServerResponse(request.request_id, False, error="MISSION_ID_EXISTS")
        now = time.time()
        mission = {
            "mission_id": mission_id,
            "objective": objective,
            "status": "planned" if actions else "blocked",
            "confidence": decision.confidence,
            "analysis": decision.analysis,
            "unknowns": list(decision.unknowns),
            "requires_research": bool(decision.requires_research),
            "actions": actions,
            "next_action": 0,
            "attempts": 0,
            "history": [],
            "created_at": now,
            "updated_at": now,
        }
        self._missions[mission_id] = mission
        self._persist_state()
        return ServerResponse(request.request_id, bool(actions), mission, None if actions else "NO_SAFE_LOCAL_PLAN")

    def _get(self, request: ServerRequest) -> ServerResponse:
        mission_id = str(request.payload.get("mission_id", "")).strip()
        if not mission_id:
            return ServerResponse(request.request_id, False, error="MISSION_ID_REQUIRED")
        mission = self._missions.get(mission_id)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        return ServerResponse(request.request_id, True, self._public_mission(mission))

    def _resume(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] in {"completed", "cancelled"}:
            return ServerResponse(request.request_id, False, error="MISSION_TERMINAL")
        if mission["next_action"] >= len(mission["actions"]):
            mission["status"] = "completed" if self._all_actions_verified(mission) else "failed"
        elif mission["status"] in {"planned", "awaiting_execution", "failed"}:
            mission["status"] = "ready"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, True, self._public_mission(mission))

    def _cancel(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] == "completed":
            return ServerResponse(request.request_id, False, error="MISSION_ALREADY_COMPLETED")
        mission["status"] = "cancelled"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, True, self._public_mission(mission))

    def _step(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        if mission["status"] in {"cancelled", "completed", "blocked"}:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_RUNNABLE")
        index = int(mission["next_action"])
        actions = mission["actions"]
        if index >= len(actions):
            mission["status"] = "completed" if self._all_actions_verified(mission) else "failed"
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, mission["status"] == "completed", self._public_mission(mission), None if mission["status"] == "completed" else "UNVERIFIED_ACTIONS")

        action = actions[index]
        mission["status"] = "executing"
        mission["attempts"] = int(mission.get("attempts", 0)) + 1
        started = time.time()
        proposal = self._proposal(action)
        if proposal is None:
            success, observation, evidence = False, "INVALID_ACTION", []
        elif proposal.tool_name:
            success, observation, evidence = False, "SERVER_TOOL_EXECUTION_NOT_YET_BOUND", []
        else:
            success, observation, evidence = self._executor(proposal)

        record = {
            "action_index": index,
            "description": str(action.get("description", "")),
            "success": bool(success),
            "observation": str(observation),
            "evidence": [str(item) for item in evidence],
            "duration": time.time() - started,
            "timestamp": time.time(),
        }
        history = mission.setdefault("history", [])
        history.append(record)
        del history[:-self.MAX_HISTORY]
        action["last_result"] = record
        action["verified"] = bool(success and evidence)
        if success and evidence:
            action["status"] = "verified"
            mission["next_action"] = index + 1
            mission["status"] = "ready" if mission["next_action"] < len(actions) else "awaiting_completion"
        else:
            action["status"] = "failed"
            mission["status"] = "failed"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, bool(success), self._public_mission(mission), None if success else "ACTION_VERIFICATION_FAILED")

    def _run(self, request: ServerRequest) -> ServerResponse:
        mission = self._mission(request)
        if mission is None:
            return ServerResponse(request.request_id, False, error="MISSION_NOT_FOUND")
        try:
            limit = int(request.payload.get("max_steps", self.MAX_RUN_STEPS))
        except (TypeError, ValueError):
            return ServerResponse(request.request_id, False, error="INVALID_MAX_STEPS")
        if limit < 1 or limit > self.MAX_RUN_STEPS:
            return ServerResponse(request.request_id, False, error="MAX_STEPS_OUT_OF_RANGE")
        if mission["status"] in {"planned", "failed", "awaiting_execution"}:
            mission["status"] = "ready"
        for _ in range(limit):
            response = self._step(ServerRequest(request.request_id, "mission.step", {"mission_id": mission["mission_id"]}))
            mission = self._missions[mission["mission_id"]]
            if mission["status"] in {"completed", "cancelled", "failed", "blocked"}:
                return ServerResponse(request.request_id, response.ok and mission["status"] == "completed", self._public_mission(mission), response.error)
        return ServerResponse(request.request_id, False, self._public_mission(mission), "RUN_STEP_LIMIT_REACHED")

    def _mission(self, request: ServerRequest) -> dict[str, Any] | None:
        mission_id = str(request.payload.get("mission_id", "")).strip()
        return self._missions.get(mission_id) if mission_id else None

    @staticmethod
    def _proposal(action: dict[str, Any]) -> ProposedAction | None:
        command = action.get("command")
        verification = action.get("verification_command")
        if command is not None and (not isinstance(command, list) or not all(isinstance(v, str) and v for v in command)):
            return None
        if verification is not None and (not isinstance(verification, list) or not all(isinstance(v, str) and v for v in verification)):
            return None
        return ProposedAction(
            description=str(action.get("description", "")),
            criterion_ids=[str(v) for v in action.get("criterion_ids", []) if isinstance(v, str)],
            command=command,
            expected_observation=str(action.get("expected_observation", "")),
            verification_command=verification,
            tool_name=str(action["tool_name"]) if action.get("tool_name") else None,
            tool_payload=dict(action["tool_payload"]) if isinstance(action.get("tool_payload"), dict) else None,
            depends_on=[str(v) for v in action.get("depends_on", []) if isinstance(v, str)],
            expected_progress=float(action.get("expected_progress", 0.5)),
            success_probability=float(action.get("success_probability", 0.5)),
            cost=float(action.get("cost", 0.0)),
            risk=float(action.get("risk", 0.0)),
            reversible=bool(action.get("reversible", True)),
            action_id=str(action["action_id"]) if action.get("action_id") else None,
        )

    @staticmethod
    def _all_actions_verified(mission: dict[str, Any]) -> bool:
        actions = mission.get("actions", [])
        return bool(actions) and all(bool(action.get("verified")) for action in actions)

    @staticmethod
    def _public_mission(mission: dict[str, Any]) -> dict[str, Any]:
        return ServerCore._json_safe(dict(mission))

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
