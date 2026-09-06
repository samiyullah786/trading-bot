from __future__ import annotations

from dataclasses import dataclass
from .task_graph import TaskGraph, TaskNode

@dataclass
class TaskSpec:
    id: str
    title: str
    depends_on: set[str]

class TaskDecomposer:
    """Builds an explicit dependency graph from structured task specifications."""

    def compile(self, specs: list[TaskSpec]) -> TaskGraph:
        graph = TaskGraph()
        pending = list(specs)
        while pending:
            progressed = False
            for spec in pending[:]:
                if all(dep in graph.nodes for dep in spec.depends_on):
                    graph.add(TaskNode(spec.id, spec.title, set(spec.depends_on)))
                    pending.remove(spec)
                    progressed = True
            if not progressed:
                unresolved = ", ".join(spec.id for spec in pending)
                raise ValueError(f"unresolvable dependency graph: {unresolved}")
        return graph
