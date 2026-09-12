from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScheduleDecision:
    ready_index: int | None
    error: str | None = None


class MissionScheduler:
    """Deterministic dependency scheduler with fail-closed plan validation."""

    def __init__(self, actions: list[dict[str, Any]], *, max_actions: int = 128) -> None:
        if len(actions) > max_actions:
            raise ValueError("PLAN_TOO_LARGE")
        self.actions = actions
        self._ids: dict[str, int] = {}
        self._validate()

    def _validate(self) -> None:
        for index, action in enumerate(self.actions):
            action_id = str(action.get("action_id", "")).strip()
            if not action_id:
                raise ValueError("ACTION_ID_REQUIRED")
            if action_id in self._ids:
                raise ValueError("DUPLICATE_ACTION_ID")
            self._ids[action_id] = index
        graph: dict[str, list[str]] = {}
        for action in self.actions:
            action_id = str(action["action_id"])
            deps = action.get("depends_on", [])
            if not isinstance(deps, list) or not all(isinstance(dep, str) and dep.strip() for dep in deps):
                raise ValueError("INVALID_DEPENDENCIES")
            if action_id in deps:
                raise ValueError("DEPENDENCY_CYCLE")
            for dep in deps:
                if dep not in self._ids:
                    raise ValueError("MISSING_DEPENDENCY")
            graph[action_id] = list(deps)
        state: dict[str, int] = {}
        def visit(node: str) -> None:
            mark = state.get(node, 0)
            if mark == 1:
                raise ValueError("DEPENDENCY_CYCLE")
            if mark == 2:
                return
            state[node] = 1
            for dep in graph[node]:
                visit(dep)
            state[node] = 2
        for node in graph:
            visit(node)

    def next_ready(self) -> ScheduleDecision:
        for index, action in enumerate(self.actions):
            if action.get("verified") or action.get("status") == "verified":
                continue
            deps = action.get("depends_on", [])
            if all(bool(self.actions[self._ids[dep]].get("verified")) for dep in deps):
                return ScheduleDecision(index)
        pending = [a for a in self.actions if not a.get("verified")]
        if pending:
            return ScheduleDecision(None, "NO_READY_ACTION")
        return ScheduleDecision(None, "COMPLETE")
