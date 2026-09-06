import unittest
from src.skills import Skill, SkillLibrary

class SkillTests(unittest.TestCase):
    def test_reliability_learning(self):
        library = SkillLibrary()
        library.register(Skill("test", "run tests"))
        library.record("test", True)
        library.record("test", False)
        self.assertEqual(library.skills["test"].reliability, 0.5)

if __name__ == "__main__":
    unittest.main()
