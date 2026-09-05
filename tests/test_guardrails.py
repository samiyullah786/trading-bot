import unittest
from src.guardrails import Policy

class GuardrailTests(unittest.TestCase):
    def test_normal_action_allowed(self):
        self.assertTrue(Policy().evaluate("run unit tests").allowed)

    def test_high_impact_action_requires_approval(self):
        decision = Policy().evaluate("delete production database", "HIGH")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_approval)

if __name__ == "__main__":
    unittest.main()
