import unittest
from src.graph import Node, TaskGraph

class GraphTests(unittest.TestCase):
    def test_dependency_readiness(self):
        g = TaskGraph()
        g.add(Node("a", "first"))
        g.add(Node("b", "second", {"a"}))
        self.assertEqual([n.id for n in g.ready()], ["a"])
        g.nodes["a"].completed = True
        self.assertEqual([n.id for n in g.ready()], ["b"])

    def test_cycle_is_rejected(self):
        g = TaskGraph()
        g.add(Node("a", "first"))
        with self.assertRaises(ValueError):
            g.add(Node("b", "second", {"b"}))

if __name__ == "__main__":
    unittest.main()
