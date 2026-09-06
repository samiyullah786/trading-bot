import unittest
from src.quality import QualityController, QualityGate

class QualityTests(unittest.TestCase):
    def test_failure_blocks_promotion(self):
        ok, failures = QualityController().evaluate([
            QualityGate("tests", True, "ok"),
            QualityGate("security", False, "missing"),
        ])
        self.assertFalse(ok)
        self.assertEqual(failures[0].name, "security")

if __name__ == "__main__":
    unittest.main()
