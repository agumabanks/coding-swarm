from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Set

@dataclass
class FileReader:
    include: Iterable[str] = field(default_factory=lambda: ("**/*.py", "**/*.md", "**/*.txt"))
    exclude: Iterable[str] = field(default_factory=lambda: (".venv", "venv", ".git", "dist", "build", "__pycache__"))
    max_bytes: int = 2_000_000
    encoding: str = "utf-8"

    def read(self, root: str | Path = ".") -> Dict[str, str]:
        root = Path(root)
        out: Dict[str, str] = {}
        exclude_dirs: Set[Path] = {root / e for e in self.exclude}
        def is_excluded(p: Path) -> bool:
            return any(ex in p.parents or p == ex for ex in exclude_dirs)
        for pattern in self.include:
            for p in root.glob(pattern):
                if p.is_file() and not is_excluded(p):
                    try:
                        data = p.read_bytes()[: self.max_bytes]
                        out[str(p)] = data.decode(self.encoding, errors="ignore")
                    except Exception:
                        pass
        return out

    # aliases
    def read_files(self, root: str | Path = "."): return self.read(root)
    def __call__(self, root: str | Path = "."): return self.read(root)

__all__ = ["FileReader"]
