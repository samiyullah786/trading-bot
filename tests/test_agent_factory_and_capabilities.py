from pathlib import Path

import pytest

from src.agent_factory import AgentFactory, AgentSpec, Evaluation, default_capabilities
from src.capability_fabric import CapabilityFabric


def test_factory_validates_and_builds_purpose_agent():
    factory = AgentFactory(default_capabilities(), lambda spec: Evaluation(True, .95, ["ok"], [], .01))
    spec = factory.build(AgentSpec("builder", "ship software", ["code", "terminal", "verification"], ["tests pass"]))
    assert spec.fingerprint()
    assert factory.evaluate(spec).passed


def test_factory_rejects_unknown_capability():
    factory = AgentFactory(default_capabilities())
    with pytest.raises(ValueError):
        factory.build(AgentSpec("x", "y", ["telepathy"]))


def test_factory_improves_only_with_passing_candidate():
    def evaluate(spec):
        score = .97 if "verification" in spec.capabilities else .80
        return Evaluation(score >= .90, score, ["gate"], [] if score >= .90 else ["weak"], .01)

    factory = AgentFactory(default_capabilities(), evaluate)
    base = AgentSpec("a", "ship", ["code"])
    better = AgentSpec("b", "ship", ["code", "verification"])
    selected = factory.improve(base, [better])
    assert selected.name == "b"


def test_capability_fabric_contains_paths_and_binds_writes(tmp_path: Path):
    fabric = CapabilityFabric(tmp_path, max_read_bytes=32)
    fabric.write_file("ok.txt", "hello")
    assert fabric.read_file("ok.txt").value == "hello"
    with pytest.raises(ValueError):
        fabric.read_file("../escape.txt")
    with pytest.raises(ValueError):
        fabric.write_file("too.txt", "x" * 33)


def test_capability_fabric_lists_directory(tmp_path: Path):
    fabric = CapabilityFabric(tmp_path)
    fabric.write_file("a.txt", "a")
    result = fabric.list_directory()
    assert "a.txt" in result.value
