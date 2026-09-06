import sys
import unittest

from src.verification import IndependentVerifier


class VerificationCommandTests(unittest.TestCase):
    def test_command_check(self):
        result = IndependentVerifier().command([sys.executable, "-c", "print('verified')"])
        self.assertTrue(result.passed)
        self.assertIn("verified", result.evidence)

    def test_missing_command_fails_cleanly(self):
        result = IndependentVerifier().command([])
        self.assertFalse(result.passed)

    def test_failed_command_is_evidence_not_exception(self):
        result = IndependentVerifier().command([sys.executable, "-c", "raise SystemExit(3)"])
        self.assertFalse(result.passed)
        self.assertIn("returncode=3", result.evidence)


if __name__ == "__main__":
    unittest.main()
