import unittest

from src.agent_controller import AgentController
from src.local_reasoner import LocalReasoner
from src.provider import ReasoningRequest


class LocalReasonerTests(unittest.TestCase):
    def test_reasoner_creates_bounded_test_plan_without_network(self):
        response = LocalReasoner().reason(ReasoningRequest("compile and test the repository", {"workspace": "."}, []))
        self.assertGreaterEqual(len(response.actions), 2)
        self.assertTrue(all(action.get("verification_command") for action in response.actions))

    def test_controller_has_local_default(self):
        decision = AgentController().decide("run tests", {"workspace": "."}, [])
        self.assertTrue(decision.actions)
        self.assertEqual(type(AgentController().provider), LocalReasoner)

    def test_unknown_objective_does_not_fabricate_a_plan(self):
        response = LocalReasoner().reason(ReasoningRequest("solve an unspecified problem", {"workspace": "."}, []))
        self.assertEqual(response.actions, [])
        self.assertEqual(response.confidence, 0.0)
        self.assertIn("specific executable strategy for this objective", response.unknowns)


if __name__ == "__main__":
    unittest.main()
