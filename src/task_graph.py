from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class TaskNode:
    id: str
    title: str
    depends_on: set[str] = field(default_factory=set)
    completed: bool = False

class TaskGraph:
    """Dependency graph for large missions."""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add(self, node: TaskNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate task: {node.id}")
        self.nodes[node.id] = node
        self._validate()

    def complete(self, task_id: str) -> None:
        self.nodes[task_id].completed = True

    def ready(self) -> list[TaskNode]:
        return [
            node for node in self.nodes.values()
            if not node.completed
            and all(self.nodes[d].completed for d in node.depends_on)
        ]

    def unresolved(self) -> list[TaskNode]:
        return [node for node in self.nodes.values() if not node.completed]

    def _validate(self) -> None:
        visiting, visited = set(), set()

        def visit(task_id: str):
            if task_id in visiting:
                raise ValueError("cyclic dependency")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in self.nodes[task_id].depends_on:
                if dependency not in self.nodes:
                    raise ValueError(f"missing dependency: {dependency}")
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in self.nodes:
            visit(task_id)
