import hashlib
import tempfile
import unittest
from pathlib import Path
from src.verification import IndependentVerifier

class VerificationTests(unittest.TestCase):
    def test_file_hash_is_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.txt"
            path.write_text("proof", encoding="utf-8")
            digest = hashlib.sha256(b"proof").hexdigest()
            result = IndependentVerifier().file_hash(str(path), digest)
            self.assertTrue(result.passed)

    def test_missing_file_fails(self):
        result = IndependentVerifier().file_exists("/definitely/not/aureon/file")
        self.assertFalse(result.passed)

if __name__ == "__main__":
    unittest.main()
