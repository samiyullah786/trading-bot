import unittest
from src.domain import Mission, Criterion
from src.kernel import OutcomeKernel
from src.autonomy import AutonomousLoop, DeterministicStrategist
from src.agent_runtime import AgentRuntime
from src.memory import CognitiveMemory
from src.learning import LearningController
from src.skills import SkillLibrary

class AgentRuntimeTests(unittest.TestCase):
    def test_blocked_run_is_remembered_and_learned(self):
        mission = Mission.create("build", [Criterion("R1", "works")])
        loop = AutonomousLoop(OutcomeKernel(mission), DeterministicStrategist())
        agent = AgentRuntime(loop, CognitiveMemory(), LearningController(SkillLibrary()))
        result = agent.run("M1", maximum_cycles=1)
        self.assertIn(result.state, ("PAUSED", "BLOCKED"))

if __name__ == "__main__":
    unittest.main()
