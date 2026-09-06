import unittest
from src.mission_factory import MissionFactory

class MissionFactoryTests(unittest.TestCase):
    def test_creates_explicit_contract(self):
        mission = MissionFactory().create("ship", ["tests pass", "deployment verified"])
        self.assertEqual(len(mission.criteria), 2)

if __name__ == "__main__":
    unittest.main()
