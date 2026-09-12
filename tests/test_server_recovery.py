import tempfile
import unittest
from pathlib import Path

from src.agent_controller import ControllerDecision
from src.autonomy import ProposedAction
from src.server_core import ServerCore
from src.server_protocol import ServerRequest


class RecoveryControllerStub:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = []

    def decide(self, objective, context, constraints):
        self.calls.append((objective, context, constraints))
        if not self.decisions:
            raise AssertionError("unexpected replanning call")
        return self.decisions.pop(0)


class ServerRecoveryTests(unittest.TestCase):
    @staticmethod
    def decision(actions):
        return ControllerDecision(actions, 0.9, [], False)

    @staticmethod
    def action(action_id, command, verification=None, depends_on=None):
        return ProposedAction(
            description=action_id,
            criterion_ids=["c1"],
            command=list(command),
            expected_observation="success",
            verification_command=list(verification) if verification else None,
            depends_on=list(depends_on or []),
            action_id=action_id,
        )

    def create_mission(self, server, mission_id):
        response = server.handle(ServerRequest("create-" + mission_id, "mission.create", {"mission_id": mission_id, "objective": "finish safely"}))
        self.assertTrue(response.ok, response.error)
        return response

    def test_failed_action_is_replanned_with_changed_strategy_and_completes(self):
        failed = self.action("original", ["python", "-c", "raise SystemExit(7)"], ["python", "-c", "raise SystemExit(0)"])
        recovery = self.action("recovery", ["python", "-c", "print('recovered')"], ["python", "-c", "print('verified')"])
        controller = RecoveryControllerStub([self.decision([failed]), self.decision([recovery])])
        with tempfile.TemporaryDirectory() as directory:
            server = ServerCore(Path(directory), controller)
            self.create_mission(server, "m1")
            response = server.handle(ServerRequest("run-m1", "mission.run", {"mission_id": "m1", "max_steps": 8}))
            self.assertTrue(response.ok, response.error)
            mission = response.result
            self.assertEqual(mission["status"], "completed")
            self.assertEqual(mission["actions"][0]["status"], "failed_terminal")
            self.assertTrue(mission["actions"][-1]["verified"])
            self.assertEqual(mission["actions"][0]["replaced_by"], ["recovery"])
            self.assertEqual(mission["recovery"]["replans"], 1)
            self.assertEqual(len(mission["history"]), 2)
            self.assertFalse(mission["history"][0]["success"])
            self.assertTrue(mission["history"][1]["success"])

    def test_unchanged_recovery_strategy_is_rejected_and_original_failure_preserved(self):
        failed = self.action("original", ["python", "-c", "raise SystemExit(7)"])
        controller = RecoveryControllerStub([self.decision([failed]), self.decision([failed])])
        with tempfile.TemporaryDirectory() as directory:
            server = ServerCore(Path(directory), controller)
            self.create_mission(server, "m2")
            response = server.handle(ServerRequest("step-m2", "mission.step", {"mission_id": "m2"}))
            self.assertFalse(response.ok)
            mission = response.result
            self.assertEqual(mission["status"], "failed")
            self.assertEqual(mission["recovery_failure"], "UNCHANGED_STRATEGY_REJECTED")
            self.assertEqual(len(mission["history"]), 1)
            self.assertEqual(mission["history"][0]["action_id"], "original")
            self.assertEqual(mission["actions"][0]["status"], "failed")

    def test_invalid_recovery_dependency_is_rejected(self):
        failed = self.action("original", ["python", "-c", "raise SystemExit(7)"])
        invalid = self.action("recovery", ["python", "-c", "print('bad')"], ["python", "-c", "print('ok')"], ["missing"])
        controller = RecoveryControllerStub([self.decision([failed]), self.decision([invalid])])
        with tempfile.TemporaryDirectory() as directory:
            server = ServerCore(Path(directory), controller)
            self.create_mission(server, "m3")
            response = server.handle(ServerRequest("step-m3", "mission.step", {"mission_id": "m3"}))
            self.assertFalse(response.ok)
            self.assertEqual(response.result["recovery_failure"], "INVALID_RECOVERY_PLAN:MISSING_DEPENDENCY")
            self.assertEqual(len(response.result["actions"]), 1)

    def test_recovery_budget_exhaustion_fails_closed(self):
        failed1 = self.action("original", ["python", "-c", "print('boom'); raise SystemExit(1)"])
        failed2 = self.action("recovery-1", ["python", "-c", "print('boom'); import sys; sys.exit(1)"])
        recovery2 = self.action("recovery-2", ["python", "-c", "print('unused')"], ["python", "-c", "print('verified')"])
        controller = RecoveryControllerStub([self.decision([failed1]), self.decision([failed2]), self.decision([recovery2])])
        with tempfile.TemporaryDirectory() as directory:
            server = ServerCore(Path(directory), controller)
            self.create_mission(server, "m4")
            response = server.handle(ServerRequest("run-m4", "mission.run", {"mission_id": "m4", "max_steps": 8}))
            self.assertFalse(response.ok)
            self.assertEqual(response.result["status"], "failed")
            self.assertEqual(response.result["recovery_failure"], "RETRY_BUDGET_EXHAUSTED")
            self.assertEqual(response.result["recovery"]["replans"], 2)

    def test_restart_preserves_recovery_lineage_and_resumes_without_replanning(self):
        failed = self.action("original", ["python", "-c", "raise SystemExit(7)"])
        recovery = self.action("recovery", ["python", "-c", "print('recovered')"], ["python", "-c", "print('verified')"])
        first_controller = RecoveryControllerStub([self.decision([failed]), self.decision([recovery])])
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            first = ServerCore(workspace, first_controller)
            self.create_mission(first, "m5")
            step = first.handle(ServerRequest("step-m5", "mission.step", {"mission_id": "m5"}))
            self.assertTrue(step.ok)
            self.assertEqual(step.result["status"], "ready")
            self.assertEqual(step.result["recovery"]["replans"], 1)

            second_controller = RecoveryControllerStub([])
            second = ServerCore(workspace, second_controller)
            status = second.handle(ServerRequest("status-m5", "mission.status", {"mission_id": "m5"}))
            self.assertTrue(status.ok)
            self.assertEqual(status.result["recovery"]["replans"], 1)
            self.assertEqual(status.result["actions"][-1]["action_id"], "recovery")

            resumed = second.handle(ServerRequest("run-m5", "mission.run", {"mission_id": "m5", "max_steps": 4}))
            self.assertTrue(resumed.ok, resumed.error)
            self.assertEqual(resumed.result["status"], "completed")
            self.assertEqual(second_controller.calls, [])
            self.assertEqual(resumed.result["actions"][0]["status"], "failed_terminal")


if __name__ == "__main__":
    unittest.main()
