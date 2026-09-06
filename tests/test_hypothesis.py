import unittest
from src.hypothesis import Hypothesis, HypothesisEngine

class HypothesisTests(unittest.TestCase):
    def test_evidence_updates_confidence(self):
        engine = HypothesisEngine()
        h = Hypothesis("bug is configuration", 0.5)
        engine.update(h, True, 0.2)
        self.assertEqual(h.confidence, 0.7)

if __name__ == "__main__":
    unittest.main()
