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
            self.assertTrue(all(isinstance(action, dict) for action in response.result["actions"]))

    def test_protocol_round_trip(self):
        request = ServerRequest("abc", "plan", {"objective": "run tests"})
        self.assertEqual(ServerRequest.from_bytes(request.to_bytes()), request)
        response = ServerResponse("abc", True, {"status": "ok"})
        self.assertEqual(ServerResponse.from_bytes(response.to_bytes()), response)

    def test_unknown_operation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = ServerCore(Path(tmp)).handle(ServerRequest("x", "delete_everything"))
            self.assertFalse(response.ok)

    def test_mission_lifecycle_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            core = ServerCore(workspace)
            planned = core.handle(ServerRequest("mission-1", "mission.create", {"objective": "run tests"}))
            self.assertTrue(planned.ok)
            mission_id = planned.result["mission_id"]

            resumed = core.handle(ServerRequest("resume-1", "mission.resume", {"mission_id": mission_id}))
            self.assertTrue(resumed.ok)
            self.assertEqual(resumed.result["status"], "ready")

            restarted = ServerCore(workspace)
            fetched = restarted.handle(ServerRequest("get-1", "mission.get", {"mission_id": mission_id}))
            self.assertTrue(fetched.ok)
            self.assertEqual(fetched.result["mission_id"], mission_id)
            self.assertEqual(fetched.result["objective"], "run tests")

    def test_cancel_is_terminal_and_step_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            planned = core.handle(ServerRequest("m", "mission.create", {"objective": "run tests"}))
            self.assertTrue(planned.ok)
            cancelled = core.handle(ServerRequest("c", "mission.cancel", {"mission_id": "m"}))
            self.assertTrue(cancelled.ok)
            self.assertEqual(cancelled.result["status"], "cancelled")
            step = core.handle(ServerRequest("s", "mission.step", {"mission_id": "m"}))
            self.assertFalse(step.ok)


if __name__ == "__main__":
    unittest.main()
