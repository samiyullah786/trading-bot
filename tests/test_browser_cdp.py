import unittest
from src.browser_cdp import ChromeDevTools

class BrowserCdpTests(unittest.TestCase):
    def test_endpoint_validation(self):
        with self.assertRaises(ValueError):
            ChromeDevTools("not-a-url")

    def test_navigation_rejects_unsafe_scheme(self):
        client = ChromeDevTools()
        class Target:
            websocket_url = "ws://127.0.0.1:9222/devtools/page/x"
        with self.assertRaises(ValueError):
            client.navigate(Target(), "file:///etc/passwd")

if __name__ == "__main__":
    unittest.main()
