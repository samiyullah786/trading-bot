import unittest
from src.mission import MissionCompiler


class MissionCompilerAdvancedTests(unittest.TestCase):
    def test_numbered_requirements_become_individual_criteria(self):
        mission = MissionCompiler().compile(
            "build it",
            ["1. tests pass\n2. docs exist\n3. deployment works"],
        )
        self.assertEqual([c.statement for c in mission.criteria], [
            "tests pass", "docs exist", "deployment works"
        ])

    def test_implicit_objective_handles_newlines_and_then(self):
        mission = MissionCompiler().compile("build API\nthen run tests\nand document it")
        self.assertEqual([c.statement for c in mission.criteria], [
            "build API", "run tests", "document it"
        ])

    def test_empty_objective_is_rejected(self):
        with self.assertRaises(ValueError):
            MissionCompiler().compile("   ")


if __name__ == "__main__":
    unittest.main()
