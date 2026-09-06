# AUREON — Autonomous Universal Execution Engine

## Status: active engineering build

AUREON is a custom-built autonomous execution and cognitive-agent research runtime.

It does not claim to be AGI or ASI. General intelligence and superintelligence are research targets that require extraordinary, reproducible evidence.

## Closed-loop architecture

MISSION
→ CONTRACT / ACCEPTANCE CRITERIA
→ CONTEXT + MEMORY
→ REASONING PROVIDER
→ METACOGNITIVE UNCERTAINTY CHECK
→ CANDIDATE ACTIONS
→ RISK / APPROVAL BOUNDARY
→ TOOL EXECUTION
→ OBSERVATION
→ EVIDENCE
→ VERIFICATION
→ ADVERSARIAL CRITIQUE
→ RECOVERY / REPLAN
→ EPISODIC MEMORY
→ LEARNING
→ VERIFIED COMPLETION

## Implemented

### Execution
- Mission contracts
- Autonomous cycles
- Task decomposition and dependency graphs
- Strategy selection
- Terminal execution boundary
- Tool routing
- Workspace containment
- Recovery controls
- Quality gates
- Adversarial critique

### Cognitive systems
- Working, episodic and semantic memory
- Hypothesis tracking and experiments
- Skill reliability learning
- Metacognition and uncertainty tracking
- Cross-domain benchmark measurement
- Transfer evaluation
- Closed-loop agent runtime

### Integration and production foundations
- Provider-independent reasoning interface
- Structured reasoning requests/responses
- Agent controller
- Human approval gate
- JSON runtime persistence with path validation
- CI workflow and regression tests

## Validation

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

## Completion standard

The repository is not considered complete merely because modules exist.

AUREON needs demonstrated end-to-end missions with:

1. a real objective,
2. planning and action selection,
3. tool execution,
4. failure recovery,
5. evidence collection,
6. independent verification,
7. reproducible results.

Only demonstrated outcomes count as completion evidence.
