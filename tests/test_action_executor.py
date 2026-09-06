import tempfile
import unittest
from src.action_executor import ActionExecutor
from src.autonomy import ProposedAction
from src.execution import TerminalExecutor

class Tests(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            ok, _, evidence = ActionExecutor(TerminalExecutor(directory))(ProposedAction("x",["R1"],["python","-c","print('ok')"]))
            self.assertTrue(ok)
            self.assertTrue(evidence)

if __name__ == "__main__":
    unittest.main()
