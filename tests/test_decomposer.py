import unittest
from src.decomposer import TaskDecomposer, TaskSpec

class DecomposerTests(unittest.TestCase):
    def test_compiles_dependencies(self):
        graph = TaskDecomposer().compile([
            TaskSpec("a", "design", set()),
            TaskSpec("b", "build", {"a"}),
        ])
        self.assertEqual([node.id for node in graph.ready()], ["a"])

if __name__ == "__main__":
    unittest.main()
