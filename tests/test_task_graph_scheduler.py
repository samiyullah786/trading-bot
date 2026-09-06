import unittest

from src.task_graph import TaskGraph, TaskNode


class TaskGraphSchedulerTests(unittest.TestCase):
    def test_priority_and_dependencies(self):
        graph = TaskGraph()
        graph.add(TaskNode("A", "prepare", priority=1))
        graph.add(TaskNode("B", "high priority", {"A"}, priority=10))
        graph.add(TaskNode("C", "low priority", {"A"}, priority=1))
        self.assertEqual([n.id for n in graph.ready()], ["A"])
        graph.complete("A")
        self.assertEqual([n.id for n in graph.ready()], ["B", "C"])
        self.assertEqual([n.id for n in graph.blocked()], [])

    def test_progress_and_dependents(self):
        graph = TaskGraph()
        graph.add(TaskNode("A", "a"))
        graph.add(TaskNode("B", "b", {"A"}))
        self.assertEqual(graph.progress(), 0.0)
        self.assertEqual([n.id for n in graph.dependents("A")], ["B"])
        graph.complete("A")
        self.assertEqual(graph.progress(), 0.5)


if __name__ == "__main__":
    unittest.main()
