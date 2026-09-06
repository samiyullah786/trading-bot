from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TaskNode:
    id: str
    title: str
    depends_on: set[str] = field(default_factory=set)
    completed: bool = False
    priority: float = 0.0
    metadata: dict = field(default_factory=dict)


class TaskGraph:
    """Dependency graph with deterministic readiness and safe mutation."""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add(self, node: TaskNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate task: {node.id}")
        candidate = dict(self.nodes)
        candidate[node.id] = node
        self._validate(candidate)
        self.nodes[node.id] = node

    def complete(self, task_id: str) -> None:
        if task_id not in self.nodes:
            raise KeyError(task_id)
        self.nodes[task_id].completed = True

    def ready(self) -> list[TaskNode]:
        ready = [
            node for node in self.nodes.values()
            if not node.completed and all(self.nodes[dependency].completed for dependency in node.depends_on)
        ]
        return sorted(ready, key=lambda n: (-n.priority, n.id))

    def blocked(self) -> list[TaskNode]:
        return [
            node for node in self.nodes.values()
            if not node.completed and any(not self.nodes[d].completed for d in node.depends_on)
        ]

    def dependents(self, task_id: str) -> list[TaskNode]:
        if task_id not in self.nodes:
            raise KeyError(task_id)
        return sorted((n for n in self.nodes.values() if task_id in n.depends_on), key=lambda n: n.id)

    def progress(self) -> float:
        if not self.nodes:
            return 1.0
        return sum(node.completed for node in self.nodes.values()) / len(self.nodes)

    @staticmethod
    def _validate(nodes: dict[str, TaskNode]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError("cyclic dependency")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in nodes[task_id].depends_on:
                if dependency not in nodes:
                    raise ValueError(f"missing dependency: {dependency}")
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in nodes:
            visit(task_id)
