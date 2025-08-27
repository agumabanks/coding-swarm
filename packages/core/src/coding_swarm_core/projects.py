# coding_swarm_core/projects.py
from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field, asdict
from hashlib import blake2b
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

# --- Optional deps (used if present; otherwise graceful fallback)
try:  # platform-specific user data dirs (XDG on Linux, etc.)
    from platformdirs import user_data_dir  # type: ignore
except Exception:  # pragma: no cover
    user_data_dir = None  # resolved by _data_home()

try:  # cross-platform file locking
    from filelock import FileLock, Timeout  # type: ignore
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore
    Timeout = None  # type: ignore


APP_NAME = "sanaa"
ORG_NAME = "coding-swarm"  # for platformdirs (macOS/Windows conventions)

# -------------------------
# Paths & storage layout
# -------------------------
def _data_home() -> Path:
    """
    Return the user data directory for Sanaa.
    Prefers platformdirs (XDG on Linux) when available, else ~/.sanaa.
    """
    if user_data_dir:
        return Path(user_data_dir(APP_NAME, ORG_NAME))
    # XDG_DATA_HOME ($HOME/.local/share) when set; else ~/.sanaa
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / f".{APP_NAME}"


DATA_HOME: Path = _data_home()
REGISTRY_DIR: Path = DATA_HOME / "projects"
REGISTRY_PATH: Path = REGISTRY_DIR / "registry.json"
JOURNALS_DIR: Path = REGISTRY_DIR / "journals"
LOCK_PATH: Path = REGISTRY_DIR / ".registry.lock"

# default ignore rules when scanning projects
DEFAULT_IGNORES: Tuple[str, ...] = (
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "node_modules", ".mypy_cache", ".ruff_cache",
    "__pycache__", "dist", "build", ".pytest_cache",
    ".DS_Store",
)

# -------------------------
# Models
# -------------------------
@dataclass
class FileIndexEntry:
    path: str          # repo-relative path (POSIX style)
    size: int          # bytes
    mtime: float       # seconds since epoch
    hash: Optional[str] = None  # short blake2b (first N bytes); None if skipped


@dataclass
class Project:
    name: str
    path: str                      # absolute path on disk
    model: str = "qwen2.5"
    notes: str = ""
    files: List[FileIndexEntry] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    # helpers ----------------
    @property
    def root(self) -> Path:
        return Path(self.path).resolve()

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "Project":
        # back-compat: tolerate older shapes
        files = [
            FileIndexEntry(**fi) if not isinstance(fi, FileIndexEntry) else fi
            for fi in d.get("files", [])
        ]
        d = dict(d)
        d["files"] = files
        return cls(**d)


# -------------------------
# Persistence primitives
# -------------------------
def _ensure_dirs() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    JOURNALS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_text(path: Path, data: str) -> None:
    """Write text atomically using a temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(str(tmp_path), str(path))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text("utf-8", errors="ignore")


class _MaybeLock:
    """
    Context manager that uses filelock if present, else a no-op.
    Locks a separate .lock file (never the data file itself).
    """
    def __init__(self, lock_path: Path, timeout: float = 10.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self._lock = None

    def __enter__(self):
        if FileLock:
            self._lock = FileLock(str(self.lock_path))
            self._lock.acquire(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._lock:
            try:
                self._lock.release()
            except Exception:
                pass
        return False


# -------------------------
# Registry
# -------------------------
@dataclass
class _RegistryDoc:
    version: int
    default: Optional[str]
    projects: Dict[str, Dict]  # name -> Project (as dict)


class ProjectRegistry:
    """
    JSON registry + JSONL journals per project.

    File layout:
      <DATA_HOME>/projects/registry.json
      <DATA_HOME>/projects/journals/<name>.journal.jsonl
    """

    SCHEMA_VERSION = 1

    def __init__(self, default: Optional[str], projects: Dict[str, Project]):
        self.default = default
        self._projects = projects

    # -------- core io
    @classmethod
    def load(cls) -> "ProjectRegistry":
        _ensure_dirs()
        with _MaybeLock(LOCK_PATH):
            raw = _read_text(REGISTRY_PATH)
            if not raw.strip():
                return cls(default=None, projects={})
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError:
                # keep a corrupted copy and reset
                backup = REGISTRY_PATH.with_suffix(".corrupted.json")
                shutil.copy(REGISTRY_PATH, backup)
                return cls(default=None, projects={})
        ver = int(doc.get("version", 0))
        default = doc.get("default")
        proj_docs = doc.get("projects", {})
        projects = {name: Project.from_dict(pdoc) for name, pdoc in proj_docs.items()}
        if ver != cls.SCHEMA_VERSION:
            # room for migrations later
            pass
        return cls(default=default, projects=projects)

    def save(self) -> None:
        _ensure_dirs()
        doc: _RegistryDoc = _RegistryDoc(
            version=self.SCHEMA_VERSION,
            default=self.default,
            projects={name: p.to_dict() for name, p in self._projects.items()},
        )
        with _MaybeLock(LOCK_PATH):
            _atomic_write_text(REGISTRY_PATH, json.dumps(asdict(doc), indent=2, ensure_ascii=False))

    # -------- CRUD
    def list(self) -> List[Project]:
        return sorted(self._projects.values(), key=lambda p: p.name.lower())

    def get(self, name: str) -> Optional[Project]:
        return self._projects.get(name)

    def upsert(self, project: Project) -> None:
        project.updated_at = time.time()
        self._projects[project.name] = project

    def delete(self, name: str) -> bool:
        existed = name in self._projects
        if existed:
            self._projects.pop(name, None)
            if self.default == name:
                self.default = None
        return existed

    def set_default(self, name: Optional[str]) -> None:
        if name is not None and name not in self._projects:
            raise KeyError(f"Unknown project '{name}'")
        self.default = name

    # -------- journals
    @staticmethod
    def _journal_path(name: str) -> Path:
        _ensure_dirs()
        return JOURNALS_DIR / f"{name}.journal.jsonl"

    def append_journal(self, name: str, entry: Dict) -> None:
        if name not in self._projects:
            raise KeyError(f"Unknown project '{name}'")
        entry = {"_ts": time.time(), "_event_id": os.urandom(8).hex(), **entry}
        p = self._journal_path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False)
        # atomic append pattern: write to temp then append+replace
        with _MaybeLock(LOCK_PATH):
            with open(p, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_journal(self, name: str, limit: Optional[int] = None) -> List[Dict]:
        if name not in self._projects:
            raise KeyError(f"Unknown project '{name}'")
        p = self._journal_path(name)
        if not p.exists():
            return []
        rows: List[Dict] = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if limit is not None:
            rows = rows[-limit:]
        return rows

    def clear_journal(self, name: str) -> None:
        p = self._journal_path(name)
        if p.exists():
            with _MaybeLock(LOCK_PATH):
                _atomic_write_text(p, "")

    # -------- scanning
    @staticmethod
    def _should_ignore(parts: Tuple[str, ...]) -> bool:
        # simple first-segment ignore (fast)
        head = parts[0]
        if head in DEFAULT_IGNORES:
            return True
        # dotfiles/folders at root get ignored by default (except .env)
        if head.startswith(".") and head not in (".env",):
            return True
        return False

    @staticmethod
    def _iter_files(root: Path) -> Iterator[Path]:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            parts = tuple(rel.split("/"))
            if not parts:
                continue
            if ProjectRegistry._should_ignore(parts):
                continue
            yield p

    @staticmethod
    def _digest(path: Path, bytes_limit: int = 64 * 1024) -> str:
        h = blake2b(digest_size=16)
        with open(path, "rb") as f:
            chunk = f.read(bytes_limit)
            h.update(chunk)
        return h.hexdigest()

    def scan(self, name: str, *, compute_hash: bool = False) -> Project:
        """
        Build/update a light index of project files.
        - hash is computed on the first 64KB by default (fast locality fingerprint)
        """
        proj = self._projects.get(name)
        if not proj:
            raise KeyError(f"Unknown project '{name}'")

        root = proj.root
        if not root.exists():
            raise FileNotFoundError(f"Project path not found: {root}")

        index: List[FileIndexEntry] = []
        for f in self._iter_files(root):
            st = f.stat()
            rel = f.relative_to(root).as_posix()
            entry = FileIndexEntry(
                path=rel,
                size=int(st.st_size),
                mtime=float(st.st_mtime),
                hash=self._digest(f) if compute_hash else None,
            )
            index.append(entry)

        proj.files = index
        proj.updated_at = time.time()
        self.upsert(proj)
        self.append_journal(name, {"event": "rescan", "files_indexed": len(index)})
        return proj

    # convenience -------------
    def upsert_from_params(
        self,
        *,
        name: str,
        path: str,
        model: str = "qwen2.5",
        notes: str = "",
        compute_hash: bool = False,
        set_default: bool = True,
    ) -> Project:
        root = Path(path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Project path does not exist: {root}")

        proj = Project(name=name, path=str(root), model=model, notes=notes)
        self.upsert(proj)
        self.scan(name, compute_hash=compute_hash)
        if set_default:
            self.set_default(name)
        self.save()
        self.append_journal(name, {"event": "add_project"})
        return proj
