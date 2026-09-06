import unittest
from src.security import EnvironmentFilter, SecurityProfile, SecretRedactor

class SecurityTests(unittest.TestCase):
    def test_default_environment_filters_secrets(self):
        env = EnvironmentFilter(SecurityProfile()).build({"SAFE": "1", "API_TOKEN": "hidden"})
        self.assertEqual(env["SAFE"], "1")
        self.assertNotIn("API_TOKEN", env)

    def test_redactor_removes_secret_values(self):
        self.assertEqual(SecretRedactor().redact("token=abc", ["abc"]), "token=[REDACTED]")

if __name__ == "__main__":
    unittest.main()
