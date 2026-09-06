import unittest
from src.agent_controller import AgentController
from src.provider import ReasoningResponse

class FakeProvider:
    def reason(self, request):
        return ReasoningResponse(
            "plan",
            [{"description":"run test","criterion_ids":["R1"],"command":["python","-V"]}],
            0.9,
            [],
        )

class AgentControllerTests(unittest.TestCase):
    def test_reasoning_becomes_candidate_action(self):
        decision = AgentController(FakeProvider()).decide("ship", {"mission":"ship"}, [])
        self.assertEqual(len(decision.actions), 1)
        self.assertFalse(decision.requires_research)

if __name__ == "__main__":
    unittest.main()
