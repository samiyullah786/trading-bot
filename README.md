# AUREON — Autonomous Universal Execution Engine

AUREON is a custom-built, outcome-driven autonomous execution system for complex digital work.

## Prime objective

Turn a user objective into a **verified real-world outcome**. Code generation is a capability, not the definition of success.

## Control loop

```text
OBSERVE → MODEL → FIND GAPS → GENERATE OPTIONS → SELECT → EXECUTE
   ↑                                                        ↓
   └──────────── VERIFY EVIDENCE ← CRITIC ← RECOVER ←──────┘
```

## Current core

- Mission compiler and explicit acceptance criteria
- Evidence-gated completion
- World observations and persistent mission state
- Candidate planning and materially-better alternative selection
- Autonomous execution loop with bounded resource controls
- Failure fingerprinting and blind-retry prevention
- Workspace containment
- Standard-library terminal execution
- Risk/approval policy boundary
- Action/evidence ledger
- Provider-independent intelligence interface
- Provider-independent browser operator contract
- Resumable mission runner

## From-scratch rule

AUREON's orchestration and control plane is custom code. It intentionally avoids autonomous-agent frameworks such as LangChain, LangGraph, AutoGen, CrewAI, OpenHands and Aider.

External model APIs may supply language/reasoning intelligence; they do not own mission truth, tool policy, completion, or persistence.

## Non-negotiable completion rule

AUREON never converts confidence into completion. Every mandatory acceptance criterion needs evidence. Failed work remains failed until a new observation demonstrates progress or success.

## Engineering direction

The next layers are being built toward a complete autonomous computer operator: structured reasoning, dependency graphs, research/evidence collection, browser execution, code/test/debug cycles, adversarial QA, deployment verification and durable recovery.

## Test

```bash
python -m unittest discover -s tests -v
```
