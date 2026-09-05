from __future__ import annotations

from pathlib import Path

class Workspace:
    """Filesystem boundary. All paths must remain inside the configured root."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative: str | Path) -> Path:
        path = (self.root / relative).resolve()
        if path != self.root and self.root not in path.parents:
            raise PermissionError("path escapes workspace")
        return path

    def read(self, relative: str | Path) -> str:
        return self._resolve(relative).read_text()

    def write(self, relative: str | Path, content: str) -> Path:
        path = self._resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def exists(self, relative: str | Path) -> bool:
        return self._resolve(relative).exists()

    def list_files(self) -> list[str]:
        return sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*")
            if path.is_file()
        )
