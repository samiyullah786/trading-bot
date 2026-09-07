import sys
import unittest

from src.action_executor import ActionExecutor, IndependentCommandVerifier
from src.autonomy import ProposedAction
from src.execution import TerminalExecutor


class IndependentVerificationEnforcementTests(unittest.TestCase):
    def test_success_without_verifier_is_not_proof(self):
        action = ProposedAction(
            "create artifact",
            ["R1"],
            command=[sys.executable, "-c", "print('created')"],
        )
        executor = ActionExecutor(TerminalExecutor())
        success, observation, evidence = executor(action)
        self.assertFalse(success)
        self.assertIn("INDEPENDENT_VERIFICATION_REQUIRED", observation)
        self.assertEqual(evidence, [])

    def test_failed_independent_verification_blocks_success(self):
        action = ProposedAction(
            "create artifact",
            ["R1"],
            command=[sys.executable, "-c", "print('created')"],
            verification_command=[sys.executable, "-c", "raise SystemExit(7)"],
        )
        terminal = TerminalExecutor()
        executor = ActionExecutor(terminal, IndependentCommandVerifier(terminal))
        success, observation, evidence = executor(action)
        self.assertFalse(success)
        self.assertIn("verification_returncode=7", observation)
        self.assertEqual(evidence, [])

    def test_independent_verification_produces_only_verifier_evidence(self):
        action = ProposedAction(
            "create artifact",
            ["R1"],
            command=[sys.executable, "-c", "print('created')"],
            verification_command=[sys.executable, "-c", "print('verified')"],
        )
        terminal = TerminalExecutor()
        executor = ActionExecutor(terminal, IndependentCommandVerifier(terminal))
        success, observation, evidence = executor(action)
        self.assertTrue(success)
        self.assertIn("verified", observation)
        self.assertEqual(len(evidence), 1)
        self.assertIn("verification_returncode=0", evidence[0])


if __name__ == "__main__":
    unittest.main()
