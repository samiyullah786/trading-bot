# AUREON Architecture

AUREON is an outcome-driven autonomous execution engine.

## Prime invariant

AUREON does not treat generated output as completion. It treats verified reality as completion.

## Control loop

OBSERVE → MODEL → GAP → PLAN → ACT → VERIFY → LEARN → REPLAN

## Layers

1. Mission layer: objective, constraints, acceptance criteria.
2. State layer: durable world state and action history.
3. Intelligence layer: provider-independent reasoning interface.
4. Planning layer: dependency-aware candidate actions.
5. Execution layer: terminal, filesystem and future browser adapters.
6. Verification layer: evidence-backed criteria.
7. Recovery layer: bounded retries requiring new evidence after failure.

## Completion

A mission completes only when every mandatory criterion is VERIFIED with evidence and no mandatory criterion remains blocked.
