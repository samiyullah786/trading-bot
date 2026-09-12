import unittest

from src.browser_verification import BrowserActionVerifier


class BrowserVerificationTests(unittest.TestCase):
    def test_passes_explicit_checks(self):
        result = BrowserActionVerifier.evaluate(
            {"url_contains": "/done", "selector": "#success", "text_contains": "Completed"},
            url="https://example.test/done",
            selector_found=True,
            page_text="Completed successfully",
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.failures, ())

    def test_reports_verification_failure(self):
        result = BrowserActionVerifier.evaluate(
            {"url_contains": "/done", "selector": "#success", "text_contains": "Completed"},
            url="https://example.test/error",
            selector_found=False,
            page_text="Something went wrong",
        )
        self.assertFalse(result.ok)
        self.assertEqual(set(result.failures), {"URL_MISMATCH", "SELECTOR_NOT_FOUND", "TEXT_NOT_FOUND"})

    def test_rejects_unknown_or_unbounded_fields(self):
        with self.assertRaises(ValueError):
            BrowserActionVerifier.validate({"run_script": "alert(1)"})
        with self.assertRaises(ValueError):
            BrowserActionVerifier.validate({"text_contains": "x" * 4097})


if __name__ == "__main__":
    unittest.main()
