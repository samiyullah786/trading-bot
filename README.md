# AUREON — Autonomous Universal Execution Engine

## Status: active engineering build

AUREON is a custom-built autonomous execution and cognitive-agent research runtime.

It does **not** claim to be AGI or ASI. Those labels require evidence far beyond architecture diagrams or unit tests.

## End-to-end execution path

MISSION
→ CONTRACT / ACCEPTANCE CRITERIA
→ MEMORY + CONTEXT
→ REASONING PROVIDER
→ METACOGNITION
→ CANDIDATE ACTIONS
→ EXECUTION BOUNDARY
→ OBSERVATION
→ EVIDENCE
→ VERIFICATION
→ CRITIQUE / RECOVERY
→ LEARNING
→ COMPLETE ONLY WHEN PROVEN

## Demonstrated integration

The repository now contains an executable end-to-end path:

- structured mission
- provider-generated executable actions
- terminal execution
- observations
- evidence attachment
- criterion verification
- verified mission completion

Run:

```bash
python examples/end_to_end_demo.py
python -m unittest discover -s tests -v
```

## Implemented foundations

### Execution
- Mission contracts
- Autonomous cycles
- Task graphs
- Strategy selection
- Tool routing
- Terminal execution
- Recovery boundaries
- Quality gates
- Adversarial critique

### Cognitive architecture
- Working / episodic / semantic memory
- Hypothesis tracking
- Experiment primitives
- Skill reliability learning
- Metacognition
- Capability benchmarks
- Transfer evaluation

### Integration
- Provider-independent reasoning interface
- Agent controller
- End-to-end mission executor
- Deterministic demo provider
- Human approval gate
- Persistent runtime state
- CI configuration
- Regression and end-to-end tests

## Honest remaining work

This is not yet a complete real-world autonomous AGI/ASI system. Major remaining work includes real browser adapters, authenticated external-service integrations, robust isolation, durable databases, deployment infrastructure, security review, richer planners, real benchmark suites, and repeated real-world mission demonstrations.
