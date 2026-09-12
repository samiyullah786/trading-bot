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

    def test_duplicate_request_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            request = ServerRequest("same-request", "mission.create", {"objective": "run tests"})
            first = core.handle(request)
            second = core.handle(request)
            self.assertTrue(first.ok)
            self.assertEqual(first, second)
            self.assertEqual(len(core._missions), 1)
            self.assertEqual(first.result["mission_id"], "same-request")

    def test_request_id_reuse_with_different_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            first = core.handle(ServerRequest("same", "mission.create", {"objective": "run tests"}))
            conflict = core.handle(ServerRequest("same", "mission.create", {"objective": "compile"}))
            self.assertTrue(first.ok)
            self.assertFalse(conflict.ok)
            self.assertEqual(conflict.error, "REQUEST_ID_REUSE_CONFLICT")
            self.assertEqual(len(core._missions), 1)

    def test_idempotency_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            request = ServerRequest("persistent-id", "mission.create", {"objective": "run tests"})
            first = ServerCore(workspace).handle(request)
            restarted = ServerCore(workspace)
            second = restarted.handle(request)
            self.assertEqual(first, second)
            self.assertEqual(len(restarted._missions), 1)

    def test_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ServerCore.STATE_FILE
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                ServerCore(Path(tmp))

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

    def test_run_executes_and_independently_verifies_each_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "tests").mkdir()
            (workspace / "src" / "sample.py").write_text("value = 1\n", encoding="utf-8")
            (workspace / "tests" / "test_sample.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n\nif __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8")
            core = ServerCore(workspace)
            planned = core.handle(ServerRequest("m", "mission.create", {"objective": "compile and test the repository"}))
            self.assertTrue(planned.ok)
            result = core.handle(ServerRequest("run-1", "mission.run", {"mission_id": "m", "max_steps": 8}))
            self.assertTrue(result.ok, result.error)
            self.assertEqual(result.result["status"], "completed")
            self.assertGreaterEqual(len(result.result["history"]), 2)
            self.assertTrue(all(entry["success"] for entry in result.result["history"]))
            self.assertTrue(all(action["verified"] for action in result.result["actions"]))

    def test_scheduler_executes_ready_independent_action_before_blocked_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            core._missions["scheduled"] = {
                "mission_id": "scheduled", "objective": "dependency scheduling", "status": "ready", "confidence": 1.0,
                "analysis": "", "unknowns": [], "requires_research": False,
                "actions": [
                    {"action_id": "dependent", "description": "dependent", "command": ["python", "-c", "print('dependent')"],
                     "verification_command": ["python", "-c", "raise SystemExit(0)"], "depends_on": ["base"], "verified": False},
                    {"action_id": "base", "description": "base", "command": ["python", "-c", "print('base')"],
                     "verification_command": ["python", "-c", "raise SystemExit(0)"], "depends_on": [], "verified": False},
                ],
                "next_action": 0, "attempts": 0, "history": [], "created_at": 0.0, "updated_at": 0.0,
            }
            first = core.handle(ServerRequest("scheduled-1", "mission.step", {"mission_id": "scheduled"}))
            self.assertTrue(first.ok, first.error)
            self.assertEqual(first.result["history"][0]["action_index"], 1)
            second = core.handle(ServerRequest("scheduled-2", "mission.step", {"mission_id": "scheduled"}))
            self.assertTrue(second.ok, second.error)
            self.assertEqual(second.result["history"][1]["action_index"], 0)
            self.assertEqual(second.result["status"], "completed")

    def test_invalid_plan_is_rejected_before_storage(self):
        class BadController:
            def decide(self, objective, context, evidence):
                class D:
                    actions = [
                        {"action_id": "a", "command": ["python", "-c", "print('a')"], "depends_on": ["missing"]}
                    ]
                    confidence = 1.0
                    analysis = ""
                    unknowns = []
                    requires_research = False
                return D()
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp), BadController())
            result = core.handle(ServerRequest("bad-plan", "mission.create", {"objective": "anything"}))
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "INVALID_PLAN:MISSING_DEPENDENCY")
            self.assertNotIn("bad-plan", core._missions)

    def test_tool_action_uses_authoritative_runtime_and_independent_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            core._missions["tool-mission"] = {
                "mission_id": "tool-mission", "objective": "execute tool", "status": "ready", "confidence": 1.0,
                "analysis": "", "unknowns": [], "requires_research": False,
                "actions": [{"action_id": "tool-action", "description": "run a tool", "criterion_ids": [],
                              "tool_name": "terminal", "tool_payload": {"argv": ["python", "-c", "print('ok')"],
                              "verification_command": ["python", "-c", "raise SystemExit(0)"]}, "verified": False}],
                "next_action": 0, "attempts": 0, "history": [], "created_at": 0.0, "updated_at": 0.0,
            }
            result = core.handle(ServerRequest("tool-step", "mission.step", {"mission_id": "tool-mission"}))
            self.assertTrue(result.ok, result.error)
            self.assertTrue(result.result["actions"][0]["verified"])
            self.assertTrue(any("verification_returncode=0" in item for item in result.result["history"][0]["evidence"]))

    def test_unverified_dependency_blocks_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            core._missions["dependency-mission"] = {
                "mission_id": "dependency-mission", "objective": "dependency", "status": "ready", "confidence": 1.0,
                "analysis": "", "unknowns": [], "requires_research": False,
                "actions": [{"action_id": "a", "description": "dependent", "criterion_ids": [], "command": ["python", "-c", "print('bad')"],
                              "verification_command": ["python", "-c", "print('ok')"], "depends_on": ["missing"], "verified": False}],
                "next_action": 0, "attempts": 0, "history": [], "created_at": 0.0, "updated_at": 0.0,
            }
            result = core.handle(ServerRequest("dependency-step", "mission.step", {"mission_id": "dependency-mission"}))
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "INVALID_PLAN:MISSING_DEPENDENCY")
            self.assertEqual(result.result["attempts"], 0)

    def test_failed_action_never_advances_or_claims_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            core = ServerCore(Path(tmp))
            planned = core.handle(ServerRequest("m", "mission.create", {"objective": "run tests"}))
            self.assertTrue(planned.ok)
            planned.result["actions"][0]["command"] = ["python", "-c", "raise SystemExit(7)"]
            planned.result["actions"][0]["verification_command"] = ["python", "-c", "raise SystemExit(0)"]
            core._missions["m"] = planned.result
            result = core.handle(ServerRequest("run-1", "mission.run", {"mission_id": "m", "max_steps": 2}))
            self.assertFalse(result.ok)
            self.assertEqual(result.result["status"], "failed")
            self.assertEqual(result.result["next_action"], 0)


if __name__ == "__main__":
    unittest.main()
