from __future__ import annotations

import json
from pathlib import Path

class JsonStore:
    """Atomic-ish local persistence for explicit runtime state."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, value: dict) -> Path:
        if "/" in name or "\\" in name or name in ("", ".", ".."):
            raise ValueError("invalid state name")
        target = self.root / f"{name}.json"
        temporary = self.root / f".{name}.tmp"
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(target)
        return target

    def load(self, name: str) -> dict | None:
        target = self.root / f"{name}.json"
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))
