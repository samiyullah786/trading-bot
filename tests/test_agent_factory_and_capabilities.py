from pathlib import Path
import tempfile
import unittest

from src.agent_factory import AgentFactory, AgentSpec, Evaluation, default_capabilities
from src.capability_fabric import CapabilityFabric


class AgentFactoryAndCapabilityTests(unittest.TestCase):
    def test_factory_validates_and_builds_purpose_agent(self):
        factory = AgentFactory(default_capabilities(), lambda spec: Evaluation(True, .95, ["ok"], [], .01))
        spec = factory.build(AgentSpec("builder", "ship software", ["code", "terminal", "verification"], ["tests pass"]))
        self.assertTrue(spec.fingerprint())
        self.assertTrue(factory.evaluate(spec).passed)

    def test_factory_rejects_unknown_capability(self):
        factory = AgentFactory(default_capabilities())
        with self.assertRaises(ValueError):
            factory.build(AgentSpec("x", "y", ["telepathy"]))

    def test_factory_improves_only_with_passing_candidate(self):
        def evaluate(spec):
            score = .97 if "verification" in spec.capabilities else .90
            return Evaluation(score >= .90, score, ["gate"], [], .01)

        factory = AgentFactory(default_capabilities(), evaluate)
        base = AgentSpec("a", "ship", ["code"])
        better = AgentSpec("b", "ship", ["code", "verification"])
        selected = factory.improve(base, [better])
        self.assertEqual(selected.name, "b")

    def test_capability_fabric_contains_paths_and_binds_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fabric = CapabilityFabric(root, max_read_bytes=32)
            fabric.write_file("ok.txt", "hello")
            self.assertEqual(fabric.read_file("ok.txt").value, "hello")
            with self.assertRaises(ValueError):
                fabric.read_file("../escape.txt")
            with self.assertRaises(ValueError):
                fabric.write_file("too.txt", "x" * 33)

    def test_capability_fabric_lists_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabric = CapabilityFabric(Path(tmp))
            fabric.write_file("a.txt", "a")
            result = fabric.list_directory()
            self.assertIn("a.txt", result.value)


if __name__ == "__main__":
    unittest.main()
