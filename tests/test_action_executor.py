import tempfile
import unittest

from src.action_executor import ActionExecutor, IndependentCommandVerifier
from src.autonomy import ProposedAction
from src.execution import TerminalExecutor


class Tests(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            terminal = TerminalExecutor(directory)
            executor = ActionExecutor(terminal, IndependentCommandVerifier(terminal))
            action = ProposedAction(
                "x",
                ["R1"],
                ["python", "-c", "print('ok')"],
                verification_command=["python", "-c", "print('verified')"],
            )
            ok, _, evidence = executor(action)
            self.assertTrue(ok)
            self.assertTrue(evidence)

    def test_success_requires_independent_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            terminal = TerminalExecutor(directory)
            verifier = IndependentCommandVerifier(terminal)
            executor = ActionExecutor(terminal, verifier)
            action = ProposedAction(
                "create marker",
                ["R1"],
                ["python", "-c", "open('marker.txt','w').write('ok')"],
                verification_command=[
                    "python",
                    "-c",
                    "from pathlib import Path; p=Path('marker.txt'); assert p.read_text() == 'ok'",
                ],
            )
            ok, observation, evidence = executor(action)
            self.assertTrue(ok)
            self.assertIn("verification_returncode=0", observation)
            self.assertEqual(len(evidence), 1)

    def test_verification_failure_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            terminal = TerminalExecutor(directory)
            executor = ActionExecutor(terminal, IndependentCommandVerifier(terminal))
            action = ProposedAction(
                "do not verify",
                ["R1"],
                ["python", "-c", "print('action ok')"],
                verification_command=["python", "-c", "raise SystemExit(3)"],
            )
            ok, _, evidence = executor(action)
            self.assertFalse(ok)
            self.assertEqual(evidence, [])


if __name__ == "__main__":
    unittest.main()
