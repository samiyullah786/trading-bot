import unittest
from src.transfer import TransferCase, TransferEvaluator

class TransferTests(unittest.TestCase):
    def test_transfer_score(self):
        score = TransferEvaluator().evaluate(TransferCase("coding", "data", 0.8, 0.64))
        self.assertAlmostEqual(score, 0.8)

if __name__ == "__main__":
    unittest.main()
