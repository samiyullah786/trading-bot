from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid

class Status(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

@dataclass
class Criterion:
    id: str
    statement: str
    mandatory: bool = True
    status: Status = Status.PENDING
    evidence: list[str] = field(default_factory=list)

@dataclass
class Observation:
    source: str
    fact: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class Action:
    id: str
    description: str
    criterion_ids: list[str]
    depends_on: list[str] = field(default_factory=list)
    status: Status = Status.PENDING
    attempts: int = 0
    fingerprints: list[str] = field(default_factory=list)
    result: str = ""

@dataclass
class Mission:
    id: str
    objective: str
    criteria: list[Criterion]
    constraints: list[str] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)

    @classmethod
    def create(cls, objective: str, criteria: list[Criterion]) -> "Mission":
        return cls(id=str(uuid.uuid4()), objective=objective, criteria=criteria)
