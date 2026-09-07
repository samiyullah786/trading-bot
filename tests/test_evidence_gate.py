import sys
import unittest

from src.autonomy import AutonomousLoop, ProposedAction
from src.domain import Criterion, Mission, Status
from src.kernel import OutcomeKernel


class EvidenceGateTests(unittest.TestCase):
    def test_success_without_evidence_cannot_verify_action(self):
        mission = Mission.create("prove", [Criterion("R1", "proven")])

        class Strategist:
            def propose(self, _mission, gaps):
                yield ProposedAction(
                    "claim success",
                    list(gaps),
                    command=[sys.executable, "-c", "print('success')"],
                )

        loop = AutonomousLoop(
            OutcomeKernel(mission),
            Strategist(),
            executor=lambda _action: (True, "tool says success", []),
        )
        result = loop.cycle()
        self.assertEqual(result["state"], "RECOVER")
        self.assertEqual(mission.criteria[0].status, Status.PENDING)
        self.assertEqual(mission.criteria[0].evidence, [])
        self.assertIn("EVIDENCE_REQUIRED", result["observation"])

    def test_verified_evidence_allows_progress(self):
        mission = Mission.create("prove", [Criterion("R1", "proven")])

        class Strategist:
            def propose(self, _mission, gaps):
                yield ProposedAction("prove", list(gaps))

        loop = AutonomousLoop(
            OutcomeKernel(mission),
            Strategist(),
            executor=lambda _action: (True, "ok", ["independent verifier: proven"]),
        )
        result = loop.cycle()
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(mission.criteria[0].status, Status.VERIFIED)
        self.assertEqual(mission.criteria[0].evidence, ["independent verifier: proven"])


if __name__ == "__main__":
    unittest.main()
