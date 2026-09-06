import sys
import tempfile
import unittest

from src.domain import Criterion, Mission
from src.execution import TerminalExecutor
from src.action_executor import ActionExecutor
from src.agent_controller import AgentController
from src.demo_provider import DeterministicMissionProvider
from src.mission_executor import EndToEndMissionExecutor

class EndToEndTests(unittest.TestCase):
    def test_provider_to_execution_to_verified_completion(self):
        with tempfile.TemporaryDirectory() as workspace:
            mission = Mission.create("demo", [
                Criterion("R1", "first command"),
                Criterion("R2", "second command"),
            ])
            provider = DeterministicMissionProvider({
                "R1": [sys.executable, "-c", "print('one')"],
                "R2": [sys.executable, "-c", "print('two')"],
            })
            result = EndToEndMissionExecutor(
                AgentController(provider),
                ActionExecutor(TerminalExecutor(workspace)),
            ).execute(mission, maximum_cycles=10)

            self.assertEqual(result.state, "COMPLETE")
            self.assertTrue(result.report["complete"])
            self.assertEqual(result.report["open_gaps"], [])

if __name__ == "__main__":
    unittest.main()
