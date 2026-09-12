from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.server_core import ServerCore
from src.server_protocol import ServerRequest, ServerResponse


class ServerCoreTests(unittest.TestCase):
    def test_health_and_plan_are_os_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            health = core.handle(ServerRequest("1", "health"))
            self.assertTrue(health.ok)
            response = core.handle(ServerRequest("2", "plan", {"objective": "compile and test the repository"}))
            self.assertTrue(response.ok)
            self.assertEqual(response.result["mission_id"], "2")
            self.assertTrue(response.result["actions"])

    def test_protocol_round_trip(self):
        request = ServerRequest("abc", "plan", {"objective": "run tests"})
        self.assertEqual(ServerRequest.from_bytes(request.to_bytes()), request)
        response = ServerResponse("abc", True, {"status": "ok"})
        self.assertEqual(ServerResponse.from_bytes(response.to_bytes()), response)

    def test_unknown_operation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = ServerCore(Path(tmp)).handle(ServerRequest("x", "delete_everything"))
            self.assertFalse(response.ok)


if __name__ == "__main__":
    unittest.main()
