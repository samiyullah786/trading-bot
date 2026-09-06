from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain import Criterion, Mission
from src.execution import TerminalExecutor
from src.action_executor import ActionExecutor
from src.agent_controller import AgentController
from src.demo_provider import DeterministicMissionProvider
from src.mission_executor import EndToEndMissionExecutor

workspace = str(ROOT)
mission = Mission.create(
    "Demonstrate end-to-end autonomous verified execution",
    [
        Criterion("R1", "Python can execute a command successfully"),
        Criterion("R2", "The autonomous loop records evidence"),
    ],
)

provider = DeterministicMissionProvider({
    "R1": ["python", "-c", "print('R1 verified')"],
    "R2": ["python", "-c", "print('R2 evidence recorded')"],
})

runner = EndToEndMissionExecutor(
    AgentController(provider),
    ActionExecutor(TerminalExecutor(workspace)),
)

result = runner.execute(mission, maximum_cycles=10)
print(result.state)
print(result.report)
if result.state != "COMPLETE":
    raise SystemExit(1)
