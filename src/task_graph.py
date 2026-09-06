from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class TaskNode:
    id: str
    title: str
    depends_on: set[str] = field(default_factory=set)
    completed: bool = False

class TaskGraph:
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
        return [n for n in self.nodes.values() if not n.completed and all(self.nodes[d].completed for d in n.depends_on)]

    def _validate(self) -> None:
        visiting, visited = set(), set()
        def visit(task_id: str):
            if task_id in visiting: raise ValueError("cyclic dependency")
            if task_id in visited: return
            visiting.add(task_id)
            for dep in self.nodes[task_id].depends_on:
                if dep not in self.nodes: raise ValueError(f"missing dependency: {dep}")
                visit(dep)
            visiting.remove(task_id); visited.add(task_id)
        for task_id in self.nodes: visit(task_id)
