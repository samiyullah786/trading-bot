import unittest

from src.security import ExecutablePolicy, SecurityProfile


class SecurityPolicyTests(unittest.TestCase):
    def test_allow_list(self):
        policy = ExecutablePolicy(SecurityProfile(allowed_executables=frozenset({"python"})))
        policy.validate("python")
        with self.assertRaises(PermissionError):
            policy.validate("curl")

    def test_unrestricted_profile_allows(self):
        ExecutablePolicy(SecurityProfile()).validate("anything")


if __name__ == "__main__":
    unittest.main()
