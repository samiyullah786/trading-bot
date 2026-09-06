import unittest
from src.task_graph import TaskGraph, TaskNode

class TaskGraphTests(unittest.TestCase):
    def test_dependencies_control_readiness(self):
        graph = TaskGraph()
        graph.add(TaskNode("design", "design"))
        graph.add(TaskNode("build", "build", {"design"}))
        self.assertEqual([node.id for node in graph.ready()], ["design"])
        graph.complete("design")
        self.assertEqual([node.id for node in graph.ready()], ["build"])

    def test_self_cycle_rejected_without_corrupting_graph(self):
        graph = TaskGraph()
        with self.assertRaises(ValueError):
            graph.add(TaskNode("a", "a", {"a"}))
        self.assertEqual(graph.nodes, {})

if __name__ == "__main__":
    unittest.main()
