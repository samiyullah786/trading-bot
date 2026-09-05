import unittest

from src.domain import Mission, Criterion, Status
from src.kernel import OutcomeKernel

class OutcomeKernelTests(unittest.TestCase):
    def test_empty_evidence_does_not_complete_mission(self):
        mission = Mission.create("test", [Criterion("a", "works")])
        self.assertFalse(OutcomeKernel(mission).verify())

    def test_evidence_verifies_mandatory_criterion(self):
        mission = Mission.create("test", [Criterion("a", "works")])
        kernel = OutcomeKernel(mission)
        kernel.add_evidence("a", "independent observation")
        self.assertTrue(kernel.verify())

    def test_optional_criterion_does_not_block_completion(self):
        mission = Mission.create("test", [
            Criterion("required", "works"),
            Criterion("optional", "nice", mandatory=False),
        ])
        kernel = OutcomeKernel(mission)
        kernel.add_evidence("required", "proof")
        self.assertTrue(kernel.verify())

if __name__ == "__main__":
    unittest.main()
