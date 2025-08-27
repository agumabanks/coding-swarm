from __future__ import annotations
import json, os, re, subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

from importlib import metadata as ilmd  # stdlib: importlib.metadata 3.8+  # noqa: E402

from .tools import FileReader

PYTEST_CMD = ["python", "-m", "pytest", "-q"]  # pytest CLI invocation is documented.  # docs: https://docs.pytest.org/en/stable/how-to/usage.html
RUFF_CMD = ["ruff", "check", "--quiet"]       # ruff basics & --fix in docs.        # docs: https://docs.astral.sh/ruff/linter/
MYPY_CMD = ["mypy", "--hide-error-codes", "--no-error-summary"]  # mypy CLI             # docs: https://mypy.readthedocs.io/en/stable/command_line.html

TRACE_RE = re.compile(r"File \"(?P<file>.+?)\", line (?P<line>\d+), in (?P<func>.+)")

@dataclass
class FailSnippet:
    file: str
    line: int
    func: str
    context: str

@dataclass
class DebugReport:
    cwd: str
    tests_output: str
    first_failure: Optional[str]
    snippet: Optional[FailSnippet]
    refs: List[str]
    ruff: str
    mypy: str
    docs: Dict[str, str]

def _run(cmd: List[str], cwd: str) -> str:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return f"[run-error] {e}"

def _first_traceback(text: str) -> Optional[str]:
    blocks = re.split(r"\n=+|\n-+\n", text)
    for b in blocks:
        if "Traceback (most recent call last)" in b:
            return b
    return None

def _extract_snippet(tb: str, root: str) -> Optional[FailSnippet]:
    m = None
    for m in TRACE_RE.finditer(tb):  # keep last (deepest) frame
        pass
    if not m:
        return None
    file, line, func = m.group("file"), int(m.group("line")), m.group("func")
    p = Path(file if os.path.isabs(file) else os.path.join(root, file))
    if not p.exists() or not p.is_file():
        return FailSnippet(file=file, line=line, func=func, context="")
    lines = p.read_text("utf-8", errors="ignore").splitlines()
    lo, hi = max(0, line - 6), min(len(lines), line + 5)
    context = "\n".join(f"{i+1:>5}: {lines[i]}" for i in range(lo, hi))
    return FailSnippet(file=str(p), line=line, func=func, context=context)

def _find_refs(root: str, keywords: List[str]) -> List[str]:
    """Very light auto-context: find files mentioning symbols from the error."""
    fr = FileReader()
    refs = []
    text_map = fr.read(root)
    for path, txt in text_map.items():
        for kw in keywords:
            if kw and kw in txt:
                refs.append(path)
                break
    return sorted(set(refs))[:40]

def _guess_symbols(tb_or_msg: str) -> List[str]:
    # simple guesses: NameError X, AttributeError: 'A' object has no attribute 'b'
    pats = [
        r"NameError: name '(.+?)' is not defined",
        r"ImportError: cannot import name '(.+?)'",
        r"AttributeError: .*? object has no attribute '(.+?)'",
        r"ModuleNotFoundError: No module named '(.+?)'",
    ]
    out = []
    for p in pats:
        out += re.findall(p, tb_or_msg)
    # also capture dotted identifiers seen in frames: package.module
    out += re.findall(r"\b([a-zA-Z_][\w\.]+)\b", tb_or_msg)
    return list(dict.fromkeys(out))[:30]

def _doc_links(mod_names: List[str]) -> Dict[str, str]:
    """Map module or distribution names to plausible docs URLs via importlib.metadata."""
    links: Dict[str, str] = {}
    for name in set(mod_names):
        # stdlib guess
        if name in {"asyncio","typing","json","pathlib","subprocess","re","http","itertools"}:
            links[name] = f"https://docs.python.org/3/library/{name}.html"
            continue
        # 3rd-party: try package distribution metadata
        try:
            # map import name -> distribution(s)
            dists = ilmd.packages_distributions().get(name, [])  # may be None
            candidates = list(dists) if dists else [name]
            for dist in candidates:
                meta = ilmd.metadata(dist)
                home = meta.get("Home-page") or ""
                proj_urls = [v for k,v in meta.items() if k.lower()=="project-url"]
                if home:
                    links[name] = home; break
                if proj_urls:
                    links[name] = proj_urls[0].split(",")[-1].strip(); break
        except Exception:
            pass
    return links

def auto_debug(root: str, user_failure: Optional[str]) -> DebugReport:
    root = str(Path(root).resolve())
    tests_out = _run(PYTEST_CMD, cwd=root) if not user_failure else ""
    tb = _first_traceback(tests_out) if tests_out else None
    tb_or_msg = user_failure or tb or tests_out
    snippet = _extract_snippet(tb_or_msg or "", root) if tb_or_msg else None

    # gather symbols and references
    symbols = _guess_symbols(tb_or_msg or "")
    refs = _find_refs(root, symbols[:10])

    ruff_out = _run(RUFF_CMD, cwd=root)
    mypy_out = _run(MYPY_CMD, cwd=root)

    # docs for symbol-leading packages (best-effort)
    maybe_mods = set()
    for s in symbols[:10]:
        head = s.split(".")[0]
        if head.isidentifier():
            maybe_mods.add(head)
    docs = _doc_links(list(maybe_mods))

    return DebugReport(
        cwd=root,
        tests_output=tests_out,
        first_failure=tb,
        snippet=snippet,
        refs=refs,
        ruff=ruff_out,
        mypy=mypy_out,
        docs=docs,
    )

def summarize_fail_report(r: DebugReport) -> str:
    parts = []
    if r.first_failure:
        parts.append("== first failure ==")
        parts.append(r.first_failure.strip())
    if r.snippet:
        parts.append("\n== code context ==")
        parts.append(f"{r.snippet.file}:{r.snippet.line} in {r.snippet.func}\n{r.snippet.context}")
    if r.refs:
        parts.append("\n== related files ==")
        parts.append("\n".join(" - "+p for p in r.refs))
    if r.ruff.strip():
        parts.append("\n== ruff ==")
        parts.append(r.ruff.strip())
    if r.mypy.strip():
        parts.append("\n== mypy ==")
        parts.append(r.mypy.strip())
    if r.docs:
        parts.append("\n== docs ==")
        parts += [f"{k}: {v}" for k,v in r.docs.items()]
    return "\n".join(parts)
