import unittest
from src.memory import CognitiveMemory, MemoryItem

class MemoryTests(unittest.TestCase):
    def test_recall_across_stores(self):
        memory = CognitiveMemory()
        memory.remember_working(MemoryItem("goal", "build compiler"))
        memory.remember_knowledge(MemoryItem("compiler", "transforms source"))
        self.assertEqual(len(memory.recall("compiler")), 2)

if __name__ == "__main__":
    unittest.main()
