from __future__ import annotations
from .autonomy import AutonomousLoop

class MissionRunner:
    def __init__(self, loop: AutonomousLoop):
        self.loop = loop
    def run(self, maximum_cycles: int = 100) -> dict:
        return self.loop.run(maximum_cycles=maximum_cycles)
