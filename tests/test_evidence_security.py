import unittest

from src.evidence import EvidenceStore


class EvidenceSecurityTests(unittest.TestCase):
    def test_secret_value_is_redacted_and_bounded(self):
        store = EvidenceStore()
        evidence = store.record(
            "criterion",
            "terminal",
            "token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 " + "x" * 5000,
        )
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ123456", evidence.observation)
        self.assertLessEqual(len(evidence.observation), 4096)
        self.assertEqual(
            evidence.digest,
            __import__("hashlib").sha256(evidence.observation.encode()).hexdigest(),
        )

    def test_evidence_count_is_bounded(self):
        store = EvidenceStore()
        store.items = [object()] * 100_000
        with self.assertRaises(ValueError):
            store.record("c", "s", "o")


if __name__ == "__main__":
    unittest.main()
