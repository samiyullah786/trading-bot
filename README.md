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

The repository contains an executable end-to-end path with structured missions, provider-generated actions, terminal execution, observations, evidence, verification, recovery, learning, and persistent runtime state.

Run:

```bash
python examples/end_to_end_demo.py
python -m unittest discover -s tests -v
```

## Native Android client

`android/` contains a dependency-light native Android application built in Java with Android platform APIs only. It provides a mobile mission console, an offline deterministic planning/execution core, a private app workspace, local artifact creation/reading, SHA-256 verification, and report export through the Android document picker.

The Android client makes no hosted AI calls and has no runtime dependency on an AI SDK, agent framework, Play Services, AndroidX, Compose, or other third-party runtime library. It is intentionally sandboxed: the mobile engine does not expose unrestricted shell access or arbitrary remote execution. Android platform/build tooling is required to compile the application.

Open the `android/` directory as a Gradle Android project and build the `app` module with an Android SDK that provides compileSdk 35.

## Launch preflight

The dependency-free `LaunchGate` performs fail-closed checks for the workspace, supported Python runtime, and required runtime imports before deployment. It is a preflight gate, not a claim of production readiness.

## Implemented foundations

### Execution
- Mission contracts
- Autonomous cycles
- Task graphs
- Strategy selection
- Unified tool runtime
- Tool routing
- Terminal execution
- Browser/CDP integration
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
- Purpose-bound agent factory with evaluated lineage
- Dependency-free local reasoning core

### Integration
- Provider-independent reasoning interface
- Agent controller
- End-to-end mission executor
- Deterministic demo provider
- Human approval gate
- Persistent runtime state
- Native Android mission console
- CI configuration
- Regression and end-to-end tests

## Remaining launch blockers

A real-world launch still requires security review, stronger OS/process isolation, browser prompt-injection defenses, authenticated external-service adapters, durable production storage, deployment/rollback infrastructure, richer benchmark suites, repeated successful real-world mission demonstrations, and a formal Android build/device test pass. These are engineering gates rather than assumed capabilities.
