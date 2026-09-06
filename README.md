# AUREON — Autonomous Universal Execution Engine

AUREON is a custom-built outcome engine designed around verified execution rather than text-only completion.

## Core loop

OBSERVE → MODEL → FIND GAPS → GENERATE OPTIONS → SELECT → EXECUTE → RECORD → VERIFY → CRITIQUE → RECOVER → REPEAT

## Current subsystems

- Mission contracts and acceptance criteria
- Evidence-gated completion
- Autonomous mission cycles
- Terminal execution boundary
- Workspace containment
- Tool routing
- Append-only action ledger
- Failure fingerprinting and bounded recovery
- Dependency-aware task graphs
- Strategy selection
- Adversarial critique
- Quality gates
- Persistent mission state
- Provider-independent intelligence boundary

## Engineering rule

An intelligence model may propose actions.

It cannot unilaterally declare the mission complete.

Completion belongs to the verification and evidence system.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Direction

The next integration stages connect the reasoning boundary, dynamic task decomposition, concrete tool routing, test/debug loops, and production verification into one durable execution runtime.
