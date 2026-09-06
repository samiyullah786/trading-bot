import unittest

from src.browser_cdp import ChromeDevTools


class BrowserHardeningTests(unittest.TestCase):
    def test_target_selection_without_network(self):
        client = ChromeDevTools()
        client.targets = lambda: []
        with self.assertRaises(Exception):
            client.select_target()

    def test_navigation_rejects_unsafe_scheme(self):
        client = ChromeDevTools()
        with self.assertRaises(ValueError):
            client.navigate(type("Target", (), {"websocket_url": "ws://localhost"})(), "file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
