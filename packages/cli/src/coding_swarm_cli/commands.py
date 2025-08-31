# packages/cli/src/coding_swarm_cli/commands.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import frontmatter  # pip install python-frontmatter
from jinja2 import Template  # pip install jinja2

# --- locations ---------------------------------------------------------------

def _global_dir() -> Path:
    # ~/.sanaa/commands
    return Path.home() / ".sanaa" / "commands"

def _project_dir(cwd: Path) -> Path:
    # <project>/.sanaa/commands (walk up to find the project root)
    root = _find_project_root(cwd) or cwd
    return root / ".sanaa" / "commands"

def _find_project_root(start: Path) -> Optional[Path]:
    # Treat a directory containing .git or pyproject.toml as a project root.
    cur = start.resolve()
    for _ in range(20):
        if (cur / ".git").is_dir() or (cur / "pyproject.toml").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None

# --- model -------------------------------------------------------------------

@dataclass(frozen=True)
class Command:
    name: str
    content: str
    source: str  # "global" | "project"
    file_path: Path
    description: Optional[str] = None
    argument_hint: Optional[str] = None

# --- helpers -----------------------------------------------------------------

def _is_markdown(name: str) -> bool:
    return name.lower().endswith(".md")

def _name_from_file(name: str) -> str:
    return name[:-3] if name.lower().endswith(".md") else name

def _load_command_file(file_path: Path, source: str) -> Optional[Command]:
    try:
        post = frontmatter.load(file_path)
    except Exception:
        return None

    desc = post.get("description")
    arg_hint = post.get("argument-hint")
    body = (post.content or "").strip()
    cmd_name = _name_from_file(file_path.name)

    return Command(
        name=cmd_name,
        content=body,
        source=source,
        file_path=file_path,
        description=desc if isinstance(desc, str) and desc.strip() else None,
        argument_hint=arg_hint if isinstance(arg_hint, str) and arg_hint.strip() else None,
    )

def _scan_dir(dir_path: Path, source: str, into: Dict[str, Command]) -> None:
    if not dir_path.exists() or not dir_path.is_dir():
        return
    for entry in dir_path.iterdir():
        if entry.is_file() and _is_markdown(entry.name):
            cmd = _load_command_file(entry, source)
            if not cmd:
                continue
            # project commands override global
            if source == "project" or cmd.name not in into:
                into[cmd.name] = cmd

# --- public API --------------------------------------------------------------

def get_commands(cwd: str | Path) -> List[Command]:
    """Return merged commands (project overrides global)."""
    cwdp = Path(cwd)
    merged: Dict[str, Command] = {}
    _scan_dir(_global_dir(), "global", merged)
    _scan_dir(_project_dir(cwdp), "project", merged)
    return list(merged.values())

def get_command(cwd: str | Path, name: str) -> Optional[Command]:
    """Direct lookup without scanning everything twice."""
    cwdp = Path(cwd)
    project_file = _project_dir(cwdp) / f"{name}.md"
    if project_file.exists():
        return _load_command_file(project_file, "project")
    global_file = _global_dir() / f"{name}.md"
    if global_file.exists():
        return _load_command_file(global_file, "global")
    return None

def run_command(cmd: Command, variables: Optional[Dict[str, str]] = None) -> str:
    """Render command content with Jinja2-like templating (simple vars)."""
    # Example: in markdown body use {{ goal }} or {{ file }}
    try:
        tmpl = Template(cmd.content)
        return tmpl.render(**(variables or {}))
    except Exception:
        # If templating fails, return raw content as a safe fallback.
        return cmd.content
