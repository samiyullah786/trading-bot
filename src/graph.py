from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class Node:
    id: str
    description: str
    depends_on: set[str] = field(default_factory=set)
    completed: bool = False
    blocked: bool = False

class TaskGraph:
    """Dependency graph with deterministic readiness and cycle protection."""
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    def add(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate node: {node.id}")
        if node.id in node.depends_on:
            raise ValueError("node cannot depend on itself")
        self.nodes[node.id] = node
        if self._has_cycle():
            del self.nodes[node.id]
            raise ValueError("dependency cycle detected")

    def ready(self) -> list[Node]:
        return [n for n in self.nodes.values() if not n.completed and not n.blocked and all(self.nodes[d].completed for d in n.depends_on)]

    def _has_cycle(self) -> bool:
        visiting, visited = set(), set()
        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for dep in self.nodes[node_id].depends_on:
                if dep not in self.nodes or visit(dep):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False
        return any(visit(i) for i in self.nodes)
