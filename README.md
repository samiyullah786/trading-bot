# AUREON — Autonomous Universal Execution Engine

## Live build status

AUREON is being built as a custom autonomous execution runtime.

### Control pipeline

```
MISSION
  ↓
MISSION CONTRACT
  ↓
TASK DECOMPOSITION
  ↓
DEPENDENCY GRAPH
  ↓
PLAN / OPTIONS
  ↓
TOOL ROUTING
  ↓
EXECUTION
  ↓
OBSERVATION + LEDGER
  ↓
EVIDENCE
  ↓
VERIFICATION + CRITIC
  ↓
RECOVERY / REPLAN
  ↓
COMPLETE ONLY WHEN PROVEN
```

### Implemented

- Mission contracts and acceptance criteria
- Evidence-gated completion
- Autonomous cycles
- Runtime orchestration
- Structured task decomposition
- Dependency graphs
- Strategy selection
- Tool routing
- Terminal execution boundary
- Workspace containment
- Append-only ledger
- Evidence store
- Failure fingerprinting and bounded recovery
- Adversarial critic
- Quality gates
- Persistent mission state
- Provider-independent intelligence interface

### Tests

```bash
python -m unittest discover -s tests -v
```

### Next engineering work

The next major integration target is connecting the existing subsystems into a single end-to-end runtime capable of receiving a structured mission, selecting executable actions, running them, collecting evidence, and recovering from failures without falsely declaring completion.
