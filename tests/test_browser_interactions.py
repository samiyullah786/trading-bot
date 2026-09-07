import unittest
from src.browser_cdp import ChromeDevTools, CdpProtocolError


class FakeCdp(ChromeDevTools):
    def __init__(self):
        pass

    def command(self, target, method, params=None):
        return {"result": {"value": True}} if method == "Runtime.evaluate" else {}


class BrowserInteractionTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeCdp()
        self.target = type("Target", (), {"websocket_url": "ws://127.0.0.1:9222/x"})()

    def test_click_uses_selector_and_is_bounded(self):
        self.assertTrue(self.client.click(self.target, "#submit"))
        with self.assertRaises(ValueError):
            self.client.click(self.target, "x" * 4097)

    def test_type_is_bounded(self):
        self.assertEqual(self.client.type_text(self.target, "hello")["inserted_bytes"], 5)
        with self.assertRaises(ValueError):
            self.client.type_text(self.target, "x" * 65537)

    def test_key_is_bounded(self):
        self.assertEqual(self.client.press_key(self.target, "Enter")["key"], "Enter")
        with self.assertRaises(ValueError):
            self.client.press_key(self.target, "x" * 65)


if __name__ == "__main__":
    unittest.main()
