# AUREON — Autonomous Universal Execution Engine

## Cognitive systems build

AUREON is evolving from an autonomous execution engine into a research architecture for increasingly general autonomous problem-solving.

It does **not** claim to be AGI or ASI.

## Current execution stack

MISSION → DECOMPOSE → PLAN → SELECT → EXECUTE → OBSERVE → EVIDENCE → VERIFY → CRITIQUE → RECOVER

## New cognitive stack

MEMORY → HYPOTHESES → EXPERIMENTS → SKILLS → METACOGNITION → TRANSFER EVALUATION

### Implemented cognitive subsystems

- Working memory
- Episodic mission memory
- Semantic knowledge memory
- Cross-store recall
- Competing hypothesis tracking
- Evidence-driven confidence updates
- Experiment specifications
- Reusable skill library
- Skill reliability tracking
- Explicit uncertainty assessment

## Capability roadmap

The project distinguishes:

1. Tool agent
2. Generalist autonomous agent
3. Adaptive learning agent
4. AGI research target
5. ASI research target

Capability claims require reproducible evidence and benchmarks.

See `docs/AGI_ASI_SCOPE.md`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Current engineering objective

Integrate the execution runtime and cognitive systems into one closed-loop architecture where experience can improve future mission selection, planning, experimentation and verification.
