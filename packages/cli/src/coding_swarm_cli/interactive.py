# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
import typer
from rapidfuzz import process as rf_process, fuzz as rf_fuzz
from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from coding_swarm_core.projects import ProjectRegistry, Project
from coding_swarm_agents.tools import FileReader
from coding_swarm_agents.diagnostics import (
    auto_debug,             # smart runner: tests + tracebacks + lint + types
    summarize_fail_report,  # human summary of the diagnostic bundle
)

# ──────────────────────────────────────────────────────────────────────────────
# Globals & Config
# ──────────────────────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False)
console = Console()

DEFAULT_BASE = os.getenv("SANAA_MODEL_BASE", "http://127.0.0.1:8080/v1")
DEFAULT_MODEL = os.getenv("SANAA_MODEL", "qwen2.5")

EXIT_WORDS = {"exit", "quit", "q", ":q", "\\q", "bye", "exist"}  # '\q' and typo included

MENU_CHOICES = ["chat", "plan", "code", "debug", "orchestrate", "projects", "help", "exit"]

DOC_HINTS: Dict[str, str] = {
    # quick links for common stacks you’re using
    "fastapi": "https://fastapi.tiangolo.com/",
    "pydantic": "https://docs.pydantic.dev/",
    "typer": "https://typer.tiangolo.com/",
    "rich": "https://rich.readthedocs.io/",
    "httpx": "https://www.python-httpx.org/",
    "sqlalchemy": "https://docs.sqlalchemy.org/",
    "uvicorn": "https://www.uvicorn.org/",
    "pytest": "https://docs.pytest.org/",
}

# ──────────────────────────────────────────────────────────────────────────────
# Pretty banner & helpers
# ──────────────────────────────────────────────────────────────────────────────

def banner() -> None:
    title = Text.assemble(
        ("Sanaa", "bold cyan"),
        ("  •  ", "dim"),
        ("architect", "white"),
        ("  •  ", "dim"),
        ("code", "white"),
        ("  •  ", "dim"),
        ("debug", "white"),
        ("  •  ", "dim"),
        ("orchestrate", "white"),
    )
    sub = Text("“Make it insanely great.”", style="dim")
    console.print(Panel.fit(Text.assemble(title, "\n", sub), border_style="cyan"))

def _client(base: Optional[str] = None) -> httpx.Client:
    # small retries via trust_env=False for deterministic proxy behavior
    return httpx.Client(base_url=base or DEFAULT_BASE, timeout=60, trust_env=False)

def _stream_chat(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    """
    SSE/streaming print. Works with OpenAI-compatible servers (e.g., llama.cpp).
    Falls back to non-stream if the server doesn’t stream.

    httpx streaming interface: .stream(...) with iter_text/iter_lines. :contentReference[oaicite:4]{index=4}
    """
    payload = {"model": model or DEFAULT_MODEL, "messages": messages, "stream": True}
    out = []
    try:
        with _client() as c, c.stream("POST", "/chat/completions", json=payload) as r:
            r.raise_for_status()
            # OpenAI-compatible SSE: lines prefixed with "data: {json}" until [DONE]. :contentReference[oaicite:5]{index=5}
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        obj.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        out.append(delta)
                        console.print(delta, end="")
                        sys.stdout.flush()
            console.print()  # newline after stream
    except Exception:
        # fallback: one-shot
        return _chat_once(messages, model=model)
    return "".join(out)

def _chat_once(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    payload = {"model": model or DEFAULT_MODEL, "messages": messages, "stream": False}
    with _client() as c:
        res = c.post("/chat/completions", json=payload)
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"]

def _fuzzy_pick(raw: str, options: Iterable[str]) -> Optional[str]:
    """
    Fuzzy-map arbitrary user text to one of `options`. RapidFuzz is fast & robust. :contentReference[oaicite:6]{index=6}
    """
    if not raw:
        return None
    match = rf_process.extractOne(raw, list(options), scorer=rf_fuzz.QRatio)
    if not match:
        return None
    choice, score, _ = match
    return choice if score >= 55 else None

def _safe_prompt(msg: str, *, default: Optional[str] = None) -> str:
    try:
        ans = Prompt.ask(msg, default=default)
    except (KeyboardInterrupt, EOFError):
        raise typer.Exit(0)
    if ans.strip().lower() in EXIT_WORDS:
        raise typer.Exit(0)
    return ans

def _project_or_select(reg: ProjectRegistry, provided: Optional[str]) -> Optional[Project]:
    # allow fuzzy name resolve too
    if provided:
        p = reg.get(provided) or reg.get(_fuzzy_pick(provided, [x.name for x in reg.list()]) or "")
        if p:
            return p
        console.print(f"[red]Project '{provided}' not found.[/red]")
    projs = reg.list()
    if not projs:
        console.print("[yellow]No projects yet. Add one in the Projects menu.[/yellow]")
        return None
    return reg.get(reg.default) or projs[0]

# ──────────────────────────────────────────────────────────────────────────────
# Context & Docs Scouts
# ──────────────────────────────────────────────────────────────────────────────

def _find_symbols_from_text(text: str) -> List[str]:
    # capture ThingError, Module.func, ClassName, snake_case_name etc.
    pats = [
        r"[A-Z][A-Za-z0-9_]*Error",       # Exceptions
        r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*",  # module.func
        r"[A-Z][A-Za-z0-9_]+",            # Classes
        r"[a-z_][a-z0-9_]+",              # funcs/vars
    ]
    rx = re.compile("|".join(f"(?:{p})" for p in pats))
    # keep order & unique
    seen, out = set(), []
    for m in rx.findall(text or ""):
        if m not in seen:
            seen.add(m); out.append(m)
    return out[:20]

def _ripgrep_search(root: str, term: str, max_hits: int = 20) -> List[Tuple[str, int, str]]:
    """Use ripgrep if present; else Python fallback."""
    if shutil.which("rg"):
        try:
            cmd = ["rg", "-n", "--no-heading", "-S", term, root]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            hits = []
            for line in out.splitlines():
                # path:line:content
                parts = line.split(":", 2)
                if len(parts) == 3:
                    hits.append((parts[0], int(parts[1]), parts[2]))
                if len(hits) >= max_hits:
                    break
            return hits
        except subprocess.CalledProcessError:
            return []
    # fallback: walk & scan
    hits: List[Tuple[str, int, str]] = []
    for p in Path(root).rglob("*.*"):
        if p.is_file() and p.suffix in {".py", ".md", ".txt", ".toml", ".yaml", ".yml"}:
            try:
                for i, line in enumerate(p.read_text("utf-8", errors="ignore").splitlines(), start=1):
                    if term in line:
                        hits.append((str(p), i, line.strip()))
                        if len(hits) >= max_hits:
                            return hits
            except Exception:
                pass
    return hits

def _suggest_docs(symbols: List[str]) -> List[str]:
    # simple mapping: if text includes known libs, show doc base URLs
    urls = []
    lower_blob = " ".join(symbols).lower()
    for key, url in DOC_HINTS.items():
        if key in lower_blob:
            urls.append(url)
    return urls[:6]

# ──────────────────────────────────────────────────────────────────────────────
# Chat / Plan / Code / Debug / Orchestrate
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def chat(project: Optional[str] = typer.Option(None, "--project", "-p"),
         stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream assistant output")):
    """Conversational chat with optional streaming."""
    reg = ProjectRegistry.load()
    proj = _project_or_select(reg, project)
    system = {"role": "system", "content":
              "You are Sanaa, a precise, senior AI coding assistant. Prefer factual answers and short code."}
    messages: List[Dict[str, str]] = [system]
    if proj:
        messages.append({"role": "system", "content": f"Project: {proj.name} at {proj.path}. Notes: {proj.notes or ''}"})
    banner()
    console.print("[dim]Type :q or \\q to exit.[/dim]")
    while True:
        user = _safe_prompt("[bold magenta]you[/bold magenta]")
        messages.append({"role": "user", "content": user})
        try:
            if stream:
                reply = _stream_chat(messages)
            else:
                reply = _chat_once(messages)
        except httpx.HTTPError as e:
            console.print(f"[red]Model error:[/red] {e}")
            continue
        console.print()
        messages.append({"role": "assistant", "content": reply})
        # light journaling
        if proj:
            reg.append_journal(proj.name, {"event": "chat", "chars": len(user)})

@app.command()
def plan(project: Optional[str] = typer.Option(None, "--project", "-p")):
    reg = ProjectRegistry.load()
    proj = _project_or_select(reg, project)
    goal = _safe_prompt("Describe your goal")
    ctx = f"Project {proj.name} at {proj.path}." if proj else "No project"
    out = _chat_once([
        {"role": "system", "content": "You are an exceptional software architect."},
        {"role": "user", "content": f"{ctx}\nCreate a step-by-step, testable plan to: {goal}"},
    ])
    console.print(Rule("[bold]Plan[/bold]"))
    console.print(Markdown(out))
    if proj:
        reg.append_journal(proj.name, {"event": "plan", "goal": goal})

@app.command()
def code(project: Optional[str] = typer.Option(None, "--project", "-p")):
    reg = ProjectRegistry.load()
    proj = _project_or_select(reg, project)
    need = _safe_prompt("What should I implement?")
    ctx = f"Project path: {proj.path}" if proj else "No project"
    out = _chat_once([
        {"role": "system", "content": "Senior Python engineer. Output clear diffs or new files sections."},
        {"role": "user", "content": f"{ctx}\nWrite code to: {need}\nReturn patch-like changes with filenames."},
    ])
    console.print(Rule("[bold]Suggested changes[/bold]"))
    console.print(Markdown(out))
    if proj:
        reg.append_journal(proj.name, {"event": "code_suggest", "topic": need})

@app.command()
def debug(project: Optional[str] = typer.Option(None, "--project", "-p")):
    """
    Smart debug:
     • Paste a traceback OR press Enter to auto-run tests & analyze failures.
     • Sanaa also scans code for likely contexts and suggests docs links.
    """
    reg = ProjectRegistry.load()
    proj = _project_or_select(reg, project)
    failure = _safe_prompt("Paste traceback / describe bug (or press Enter to auto-detect)", default="")
    # Run the diagnostic bundle
    report = auto_debug(proj.path if proj else ".", user_failure=failure or None)
    console.print(Rule("[bold]Debug report[/bold]"))
    console.print(Markdown(summarize_fail_report(report)))
    # Context Scout
    symbols = _find_symbols_from_text(failure or json.dumps(report)[:20000])
    for s in symbols[:6]:
        hits = _ripgrep_search(proj.path if proj else ".", s, max_hits=6)
        if hits:
            table = Table(box=box.SIMPLE, title=f"Context: '{s}'")
            table.add_column("File"); table.add_column("Line", justify="right"); table.add_column("Snippet")
            for pth, ln, snippet in hits:
                table.add_row(pth, str(ln), snippet)
            console.print(table)
    # Docs Scout
    for url in _suggest_docs(symbols):
        console.print(f"[dim]docs[/dim] → {url}")
    if proj:
        reg.append_journal(proj.name, {"event": "debug", "symbols": symbols[:8]})

@app.command()
def orchestrate(goal: Optional[str] = typer.Argument(None),
                project: Optional[str] = typer.Option(None, "--project", "-p")):
    """Break complex goals into tasks for multi-agent execution."""
    reg = ProjectRegistry.load()
    proj = _project_or_select(reg, project)
    if not goal:
        goal = _safe_prompt("What complex goal should I orchestrate?")
    ctx = f"Project {proj.name} at {proj.path}" if proj else "No project"
    out = _chat_once([
        {"role": "system", "content": "You are an orchestrator that decomposes work into milestones & tasks."},
        {"role": "user", "content": f"{ctx}\nDecompose into tasks and include acceptance criteria:\n{goal}"},
    ])
    console.print(Rule("[bold]Task graph[/bold]"))
    console.print(Markdown(out))
    if proj:
        reg.append_journal(proj.name, {"event": "orchestrate", "goal": goal})

# ──────────────────────────────────────────────────────────────────────────────
# Projects Menu (premium)
# ──────────────────────────────────────────────────────────────────────────────

projects = typer.Typer(help="Manage remembered projects")
app.add_typer(projects, name="projects")

@projects.command("list")
def projects_list():
    reg = ProjectRegistry.load()
    projs = reg.list()
    table = Table(title="Projects", show_lines=False, box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("#", justify="right"); table.add_column("Name", style="bold")
    table.add_column("Path"); table.add_column("Model"); table.add_column("Default", justify="center")
    for i, p in enumerate(projs, 1):
        table.add_row(str(i), p.name, p.path, p.model, "★" if reg.default == p.name else "")
    console.print(table)
    if not projs:
        console.print("[dim]No projects saved. Run `sanaa projects add`.[/dim]")

@projects.command("add")
def projects_add():
    reg = ProjectRegistry.load()
    name = _safe_prompt("Project name")
    path = _safe_prompt("Path", default=str(Path.cwd()))
    model = _safe_prompt("Model id", default=DEFAULT_MODEL)
    notes = _safe_prompt("Notes", default="")
    # lightweight index now; content on demand
    fr = FileReader()
    try:
        index = [{"path": p, "size": len(txt)} for p, txt in fr.read(path).items()]
    except Exception:
        index = []
    proj = Project(name=name, path=path, model=model, notes=notes, files=index)
    reg.upsert(proj); reg.set_default(name); reg.save()
    reg.append_journal(name, {"event":"add_project","files_indexed":len(index)})
    console.print(f"[green]Saved[/green] {name} with {len(index)} indexed files.")

@projects.command("scan")
def projects_scan(project: Optional[str] = typer.Option(None, "--project", "-p")):
    reg = ProjectRegistry.load()
    proj = reg.get(project) or reg.get(_fuzzy_pick(project or "", [x.name for x in reg.list()]) or "")
    if not proj:
        console.print("[red]Unknown project[/red]"); raise typer.Exit(1)
    fr = FileReader()
    index = [{"path": p, "size": len(txt)} for p, txt in fr.read(proj.path).items()]
    proj.files = index; reg.upsert(proj); reg.save()
    reg.append_journal(proj.name, {"event":"rescan","files_indexed":len(index)})
    console.print(f"[green]Re-indexed[/green] {len(index)} files for {proj.name}.")

# ──────────────────────────────────────────────────────────────────────────────
# Interactive menu as default entry (premium UX)
# ──────────────────────────────────────────────────────────────────────────────

def _menu_pick() -> str:
    raw = _safe_prompt("What can I help with? (chat/plan/code/debug/orchestrate/projects/help/exit)")
    if raw.lower() in EXIT_WORDS:
        raise typer.Exit(0)
    # first try exact/choices, then fuzzy
    fuzzy = _fuzzy_pick(raw.lower(), MENU_CHOICES)
    return fuzzy or raw.lower()

def _show_help_card() -> None:
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("chat", "Talk naturally. Use --no-stream to print as a block.")
    table.add_row("plan", "Generate an architected plan.")
    table.add_row("code", "Get patch-style suggestions.")
    table.add_row("debug", "Auto-run tests, analyze failures, show context & docs.")
    table.add_row("orchestrate", "Break big goals into tasks with acceptance criteria.")
    table.add_row("projects", "Add/list/scan projects; picks default automatically.")
    table.add_row("exit", "Leave the CLI. Also: q, :q, \\q, quit, exist.")
    console.print(Panel(table, title="[b]Sanaa modes[/b]", border_style="cyan"))

@app.callback(invoke_without_command=True)
def entry(ctx: typer.Context):
    if ctx.invoked_subcommand:
        return
    reg = ProjectRegistry.load()
    while True:
        banner()
        choice = _menu_pick()
        if choice in {"exit"}:
            console.print("[dim]Goodbye![/dim]"); raise typer.Exit(0)
        if choice == "help":
            _show_help_card(); continue
        if choice == "projects":
            ctx.invoke(projects_list);  # show
            if Confirm.ask("Add or scan a project now?", default=False):
                action = _safe_prompt("(a)dd / (s)can / (n)ope", default="n").lower()
                if action.startswith("a"):
                    ctx.invoke(projects_add)
                elif action.startswith("s"):
                    name = _safe_prompt("Project name to scan", default=reg.default or "")
                    ctx.invoke(projects_scan, project=name)
            continue
        # Normal flows pick (or infer) a project
        picked = reg.default or None
        # Fuzzy confirmation is handled inside the command as needed
        if choice == "chat": ctx.invoke(chat, project=picked)
        elif choice == "plan": ctx.invoke(plan, project=picked)
        elif choice == "code": ctx.invoke(code, project=picked)
        elif choice == "debug": ctx.invoke(debug, project=picked)
        elif choice == "orchestrate": ctx.invoke(orchestrate, project=picked)
        else:
            console.print(f"[red]Unknown choice[/red]: {choice}")
