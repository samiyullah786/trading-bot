import unittest

from src.mission_contract import ContractAnalyzer


class ContractAnalyzerTests(unittest.TestCase):
    def test_detects_constraint_types(self):
        requirements = ContractAnalyzer().analyze([
            "All generated files must be inside the workspace.",
            "Never expose secrets.",
            "Create at least three tests.",
        ])
        self.assertEqual(len(requirements), 3)
        self.assertIn("quantitative constraint", requirements[2].verification_hint)
        self.assertIn("negative constraint", requirements[1].verification_hint)

    def test_reports_missing_verification_hints(self):
        requirements = ContractAnalyzer().analyze(["Build the feature."])
        self.assertEqual(ContractAnalyzer().completeness_gaps(requirements), ["C1:verification-method-unspecified"])


if __name__ == "__main__":
    unittest.main()
