# AUREON — Autonomous Universal Execution Engine

AUREON is a custom-built, outcome-driven autonomous execution system.

## Mission

AUREON is designed to work toward **verified outcomes**, not merely generate code or complete a checklist.

Its governing loop is:

```
OBSERVE
  ↓
MODEL REALITY
  ↓
FIND GAPS
  ↓
PROPOSE OPTIONS
  ↓
SELECT ACTION
  ↓
EXECUTE
  ↓
VERIFY WITH EVIDENCE
  ↓
RECOVER / REPLAN
  ↓
REPEAT UNTIL PROVEN COMPLETE
```

## From-scratch rule

The following AUREON systems are implemented as custom project code:

- mission model
- outcome kernel
- acceptance criteria
- evidence accounting
- planning
- action protocol
- autonomous loop
- recovery logic
- persistence
- workspace boundary
- terminal execution boundary
- verification

AUREON deliberately does **not** depend on LangChain, LangGraph, AutoGen, CrewAI, OpenHands, Aider, or another autonomous-agent framework.

## Current capabilities

- Persistent missions
- Mandatory acceptance criteria
- Evidence-based completion
- Gap detection
- Dependency-aware action readiness
- Deterministic action planning
- Custom autonomous control loop
- Failure fingerprinting
- Blind-retry prevention
- Workspace containment
- Terminal execution through the Python standard library
- Provider-independent intelligence interface

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Important engineering principle

AUREON's intelligence provider can suggest what to do.

**Only the AUREON verification system can determine whether the mission is complete.**

## Roadmap

### Next
1. Action executor that connects plans to terminal/file tools
2. Structured intelligence adapter
3. Long-running mission scheduler
4. Browser operator boundary
5. Research/evidence subsystem
6. Adversarial critic
7. Production deployment verifier
8. Multi-agent specialisation under one mission controller
