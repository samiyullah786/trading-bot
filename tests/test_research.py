import unittest
from src.research import Evidence, EvidenceStore

class EvidenceTests(unittest.TestCase):
    def test_deduplicates_identical_evidence(self):
        store = EvidenceStore()
        item = Evidence("test", "claim", "proof")
        store.add(item); store.add(item)
        self.assertEqual(len(store.all()), 1)

if __name__ == "__main__":
    unittest.main()
