from __future__ import annotations

import hashlib
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
from .builtin_tools import TerminalTool
from .command_router import CommandRouter
from .execution import TerminalExecutor
from .mission_scheduler import MissionScheduler
from .server_protocol import ServerRequest, ServerResponse
from .tool_runtime import ToolRuntime, Verification
from .tools import ToolRegistry, ToolRequest, ToolResult


class ServerCore:
    """OS-neutral authoritative AUREON brain boundary."""

    STATE_FILE = ".aureon-missions.json"
    MAX_ACTIONS = 128
    MAX_HISTORY = 256
    MAX_RUN_STEPS = 32
    MAX_REQUEST_CACHE = 1024
    MAX_STATE_BYTES = 10_000_000

    def __init__(self, workspace: Path, controller: AgentController | None = None) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.controller = controller or AgentController()
        self._state_path = self.workspace / self.STATE_FILE
        self._lock = threading.RLock()
        self._missions: dict[str, dict[str, Any]] = {}
        self._request_cache: dict[str, tuple[str, ServerResponse]] = {}
        self._terminal = TerminalExecutor(self.workspace)
        self._executor = ActionExecutor(self._terminal, IndependentCommandVerifier(self._terminal))
        self._tools = ToolRegistry()
        self._tools.register(TerminalTool(CommandRouter(self._terminal)))
        self._tool_runtime = ToolRuntime(self._tools, self._verify_tool_result)
        self._load_state()

    @staticmethod
    def _fingerprint(request: ServerRequest) -> str:
        canonical = json.dumps({"operation": request.operation, "payload": request.payload, "protocol_version": request.protocol_version}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def handle(self, request: ServerRequest) -> ServerResponse:
        with self._lock:
            fingerprint = self._fingerprint(request)
            cached = self._request_cache.get(request.request_id)
            if cached is not None:
                cached_fingerprint, cached_response = cached
                if cached_fingerprint != fingerprint:
                    return ServerResponse(request.request_id, False, error="REQUEST_ID_REUSE_CONFLICT")
                return cached_response
            try:
                if request.operation == "health":
                    response = ServerResponse(request.request_id, True, {"status": "ready", "protocol": request.protocol_version})
                elif request.operation in {"plan", "mission.create"}:
                    response = self._plan(request)
                elif request.operation in {"mission.get", "mission.status"}:
                    response = self._get(request)
                elif request.operation == "mission.resume":
                    response = self._resume(request)
                elif request.operation == "mission.cancel":
                    response = self._cancel(request)
                elif request.operation == "mission.step":
                    response = self._step(request)
                elif request.operation == "mission.run":
                    response = self._run(request)
                else:
                    response = ServerResponse(request.request_id, False, error="UNSUPPORTED_OPERATION")
            except Exception as exc:
                response = ServerResponse(request.request_id, False, error=f"INTERNAL_ERROR:{type(exc).__name__}")
            self._remember_request(request.request_id, fingerprint, response)
            return response

    def _remember_request(self, request_id: str, fingerprint: str, response: ServerResponse) -> None:
        self._request_cache[request_id] = (fingerprint, response)
        while len(self._request_cache) > self.MAX_REQUEST_CACHE:
            del self._request_cache[next(iter(self._request_cache))]
        self._persist_state()

    def _validate_actions(self, actions: list[dict[str, Any]]) -> str | None:
        try:
            MissionScheduler(actions, max_actions=self.MAX_ACTIONS)
        except ValueError as exc:
            return str(exc)
        return None

    def _plan(self, request: ServerRequest) -> ServerResponse:
        objective = str(request.payload.get("objective", "")).strip()
        if not objective:
            return ServerResponse(request.request_id, False, error="OBJECTIVE_REQUIRED")
        decision = self.controller.decide(objective, {"workspace": str(self.workspace)}, [])
        actions = [self._json_safe(action) for action in decision.actions]
        if len(actions) > self.MAX_ACTIONS:
            return ServerResponse(request.request_id, False, error="PLAN_TOO_LARGE")
        scheduler_error = self._validate_actions(actions)
        if scheduler_error is not None:
            return ServerResponse(request.request_id, False, error=f"INVALID_PLAN:{scheduler_error}")
        mission_id = str(request.payload.get("mission_id", request.request_id)).strip() or request.request_id
        if mission_id in self._missions:
            return ServerResponse(request.request_id, False, error="MISSION_ID_EXISTS")
        now = time.time()
        mission = {"mission_id": mission_id, "objective": objective, "status": "planned" if actions else "blocked", "confidence": decision.confidence, "analysis": getattr(decision, "analysis", ""), "unknowns": list(decision.unknowns), "requires_research": bool(decision.requires_research), "actions": actions, "next_action": 0, "attempts": 0, "history": [], "created_at": now, "updated_at": now}
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
        scheduler_error = self._validate_actions(mission.get("actions", []))
        if scheduler_error is not None:
            mission["status"] = "failed"
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, False, self._public_mission(mission), f"INVALID_PLAN:{scheduler_error}")
        if self._all_actions_verified(mission):
            mission["status"] = "completed"
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
        actions = mission.get("actions", [])
        scheduler_error = self._validate_actions(actions)
        if scheduler_error is not None:
            mission["status"] = "failed"
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, False, self._public_mission(mission), f"INVALID_PLAN:{scheduler_error}")
        scheduler = MissionScheduler(actions, max_actions=self.MAX_ACTIONS)
        decision = scheduler.next_ready()
        if decision.error == "COMPLETE":
            mission["status"] = "completed"
            mission["next_action"] = len(actions)
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, True, self._public_mission(mission))
        if decision.ready_index is None:
            mission["status"] = "failed"
            mission["updated_at"] = time.time()
            self._persist_state()
            return ServerResponse(request.request_id, False, self._public_mission(mission), decision.error or "NO_READY_ACTION")
        index = decision.ready_index
        action = actions[index]
        mission["status"] = "executing"
        mission["attempts"] = int(mission.get("attempts", 0)) + 1
        started = time.time()
        proposal = self._proposal(action)
        if proposal is None:
            success, observation, evidence = False, "INVALID_ACTION", []
        elif proposal.tool_name:
            success, observation, evidence = self._execute_tool(proposal)
        else:
            success, observation, evidence = self._executor(proposal)
        record = {"action_index": index, "description": str(action.get("description", "")), "success": bool(success), "observation": str(observation), "evidence": [str(item) for item in evidence], "duration": time.time() - started, "timestamp": time.time()}
        history = mission.setdefault("history", [])
        history.append(record)
        del history[:-self.MAX_HISTORY]
        action["last_result"] = record
        action["verified"] = bool(success and evidence)
        if success and evidence:
            action["status"] = "verified"
            mission["next_action"] = index + 1
            mission["status"] = "completed" if self._all_actions_verified(mission) else "ready"
        else:
            action["status"] = "failed"
            mission["status"] = "failed"
        mission["updated_at"] = time.time()
        self._persist_state()
        return ServerResponse(request.request_id, bool(success), self._public_mission(mission), None if success else f"ACTION_VERIFICATION_FAILED:{observation[:512]}")

    def _execute_tool(self, proposal: ProposedAction) -> tuple[bool, str, list[str]]:
        payload = dict(proposal.tool_payload or {})
        if proposal.command and proposal.tool_name == "terminal" and "argv" not in payload:
            payload["argv"] = list(proposal.command)
        intent = str(payload.pop("intent", "execute"))
        request = ToolRequest(proposal.action_id or "server-action", intent, payload, proposal.expected_observation, str(proposal.risk))
        result = self._tool_runtime.execute(proposal.tool_name or "", request)
        evidence = list(result.evidence)
        if result.verification and result.verification.evidence:
            evidence.extend(item for item in result.verification.evidence if item not in evidence)
        return result.success, result.observation, evidence

    def _verify_tool_result(self, request: ToolRequest, result: ToolResult) -> Verification:
        if not result.success:
            return Verification(False, tuple(result.evidence), "TOOL_RESULT_FAILED")
        if request.intent != "execute" or not isinstance(request.payload, dict):
            return Verification(bool(result.evidence), tuple(result.evidence), "TOOL_EVIDENCE_CHECK")
        verification = request.payload.get("verification_command")
        if verification is None:
            return Verification(bool(result.evidence), tuple(result.evidence), "TOOL_EVIDENCE_CHECK")
        if not isinstance(verification, list) or not all(isinstance(item, str) and item for item in verification):
            return Verification(False, (), "INVALID_VERIFICATION_COMMAND")
        checked = self._terminal.run(verification)
        observation = f"verification_returncode={checked.returncode}; stdout={checked.stdout}; stderr={checked.stderr}"
        if checked.success:
            return Verification(True, (observation,), observation)
        return Verification(False, (), observation)

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
        try:
            return ProposedAction(description=str(action.get("description", "")), criterion_ids=[str(v) for v in action.get("criterion_ids", []) if isinstance(v, str)], command=command, expected_observation=str(action.get("expected_observation", "")), verification_command=verification, tool_name=str(action["tool_name"]) if action.get("tool_name") else None, tool_payload=dict(action["tool_payload"]) if isinstance(action.get("tool_payload"), dict) else None, depends_on=[str(v) for v in action.get("depends_on", []) if isinstance(v, str)], expected_progress=float(action.get("expected_progress", 0.5)), success_probability=float(action.get("success_probability", 0.5)), cost=float(action.get("cost", 0.0)), risk=float(action.get("risk", 0.0)), reversible=bool(action.get("reversible", True)), action_id=str(action["action_id"]) if action.get("action_id") else None)
        except (TypeError, ValueError):
            return None

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
            if len(raw) > self.MAX_STATE_BYTES:
                raise ValueError("state exceeds limit")
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("state must be an object")
            if "missions" in value or "requests" in value:
                missions, requests = value.get("missions"), value.get("requests")
                if not isinstance(missions, dict) or not isinstance(requests, dict):
                    raise ValueError("invalid state envelope")
                self._missions = {str(k): v for k, v in missions.items() if isinstance(v, dict)}
                for request_id, item in requests.items():
                    if not isinstance(item, dict) or not isinstance(item.get("fingerprint"), str) or not isinstance(item.get("response"), dict):
                        continue
                    try:
                        response = ServerResponse.from_dict(item["response"])
                    except (TypeError, ValueError, KeyError):
                        continue
                    self._request_cache[str(request_id)] = (item["fingerprint"], response)
                while len(self._request_cache) > self.MAX_REQUEST_CACHE:
                    del self._request_cache[next(iter(self._request_cache))]
                return
            self._missions = {str(k): v for k, v in value.items() if isinstance(v, dict)}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise RuntimeError("CORRUPT_MISSION_STATE")

    def _persist_state(self) -> None:
        requests = {rid: {"fingerprint": fp, "response": response.to_dict()} for rid, (fp, response) in self._request_cache.items()}
        payload = json.dumps({"missions": self._missions, "requests": requests}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(payload) > self.MAX_STATE_BYTES:
            raise ValueError("mission state exceeds limit")
        temporary = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, self._state_path)

    def snapshot(self) -> bytes:
        with self._lock:
            return json.dumps(self._missions, sort_keys=True, separators=(",", ":")).encode("utf-8")
