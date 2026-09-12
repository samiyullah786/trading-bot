import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.capability_fabric import CapabilityFabric
from src.security import SecurityProfile


class NetworkPolicyTests(unittest.TestCase):
    def test_network_is_denied_by_default(self):
        self.assertFalse(SecurityProfile().allow_network)

    def test_private_and_loopback_targets_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabric = CapabilityFabric(Path(tmp), security_profile=SecurityProfile(allow_network=True))
            for url in (
                "http://127.0.0.1/",
                "http://localhost/",
                "http://10.0.0.1/",
                "http://192.168.1.1/",
                "http://169.254.169.254/",
                "http://[::1]/",
            ):
                with self.subTest(url=url):
                    with self.assertRaises(PermissionError):
                        fabric.fetch_http(url)

    def test_public_target_can_be_allowlisted_without_network_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabric = CapabilityFabric(
                Path(tmp),
                security_profile=SecurityProfile(allow_network=True),
                allowed_http_hosts={"example.com"},
            )
            with patch("src.capability_fabric.socket.getaddrinfo", return_value=[
                (2, 1, 6, "", ("93.184.216.34", 443)),
            ]):
                self.assertEqual(fabric.validate_http_url("https://example.com/"), "example.com")

    def test_non_allowlisted_public_host_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabric = CapabilityFabric(
                Path(tmp),
                security_profile=SecurityProfile(allow_network=True),
                allowed_http_hosts={"example.com"},
            )
            with self.assertRaises(PermissionError):
                fabric.validate_http_url("https://example.org/")

    def test_resolved_private_address_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabric = CapabilityFabric(Path(tmp), security_profile=SecurityProfile(allow_network=True))
            with patch("src.capability_fabric.socket.getaddrinfo", return_value=[
                (2, 1, 6, "", ("10.0.0.7", 80)),
            ]):
                with self.assertRaises(PermissionError):
                    fabric.validate_http_url("https://example.com/")


if __name__ == "__main__":
    unittest.main()
