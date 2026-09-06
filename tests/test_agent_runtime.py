import tempfile
import unittest

from src.agent_runtime import AgentRuntime
from src.autonomy import AutonomousLoop, DeterministicStrategist
from src.checkpoint import CheckpointStore
from src.domain import Criterion, Mission
from src.kernel import OutcomeKernel
from src.learning import LearningController
from src.memory import CognitiveMemory
from src.skills import SkillLibrary


class AgentRuntimeTests(unittest.TestCase):
    def test_blocked_run_is_remembered_and_learned(self):
        mission = Mission.create("build", [Criterion("R1", "works")])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        agent = AgentRuntime(loop, CognitiveMemory(), LearningController(SkillLibrary()))
        result = agent.run(mission.id, maximum_cycles=1)
        self.assertEqual(result.state, "PAUSED")

    def test_checkpoint_is_written_and_can_restore(self):
        mission = Mission.create("build", [Criterion("R1", "works")])
        with tempfile.TemporaryDirectory() as directory:
            checkpoints = CheckpointStore(directory)
            loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
            agent = AgentRuntime(
                loop,
                CognitiveMemory(),
                LearningController(SkillLibrary()),
                checkpoints=checkpoints,
            )
            result = agent.run(mission.id, maximum_cycles=1)
            self.assertEqual(result.state, "PAUSED")
            restored = checkpoints.load(mission.id)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.id, mission.id)
            self.assertEqual(restored.criteria[0].id, "R1")

            replacement = Mission.create("different", [Criterion("X", "other")])
            replacement_loop = AutonomousLoop(OutcomeKernel(replacement), DeterministicStrategist())
            resumed = AgentRuntime(
                replacement_loop,
                CognitiveMemory(),
                LearningController(SkillLibrary()),
                checkpoints=checkpoints,
            )
            self.assertTrue(resumed.restore_checkpoint(mission.id))
            self.assertEqual(resumed.loop.kernel.mission.id, mission.id)
            self.assertEqual(resumed.loop.kernel.mission.criteria[0].id, "R1")


if __name__ == "__main__":
    unittest.main()
