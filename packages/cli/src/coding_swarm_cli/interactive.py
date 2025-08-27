import json, os, re, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.prompt import Prompt

from coding_swarm_core.projects import ProjectRegistry, Project
from coding_swarm_agents.tools import FileReader
from coding_swarm_agents.diagnostics import (
    auto_debug,             # new: test-run + traceback + refs + lint + types
    summarize_fail_report,  # formats the diagnostic bundle for display
)

app = typer.Typer(add_completion=False, help="Sanaa — interactive CLI")
console = Console()

DEFAULT_BASE = os.getenv("SANAA_MODEL_BASE", "http://127.0.0.1:8080/v1")
DEFAULT_MODEL = os.getenv("SANAA_MODEL", "qwen2.5")

EXIT_WORDS = {"exit", "quit", "q", ":q", "bye"}


# -------------------------
# swag banner + helpers
# -------------------------
def banner():
    title = "[b cyan]Sanaa[/b cyan]  •  architect  •  code  •  debug  •  orchestrate"
    sub = "[dim]“Make it insanely great.”[/dim]"
    console.print(Panel.fit(title + "\n" + sub, border_style="cyan", padding=(1,3)))

def safe_ask(prompt: str, *, default: Optional[str] = None) -> Optional[str]:
    """Prompt that recognizes global exit words everywhere."""
    val = Prompt.ask(prompt, default=default) if default is not None else Prompt.ask(prompt)
    if val and val.strip().lower() in EXIT_WORDS:
        raise typer.Exit(code=0)
    return val

def _client(base: Optional[str] = None) -> httpx.Client:
    return httpx.Client(base_url=base or DEFAULT_BASE, timeout=60)

def _chat_once(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    payload = {"model": model or DEFAULT_MODEL, "messages": messages, "stream": False}
    with _client() as c:
        res = c.post("/chat/completions", json=payload)
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"]

def _coerce_project_arg(arg: Any) -> Optional[str]:
    # When ctx.invoke() is used without explicit args, Typer may pass an OptionInfo object.
    return arg if isinstance(arg, str) else None

def _pick_project(reg: ProjectRegistry, provided: Optional[str]) -> Optional[Project]:
    provided = _coerce_project_arg(provided)
    if provided:
        p = reg.get(provided)
        if not p:
            rprint(f"[red]Project '{provided}' not found.[/red]")
        return p
    items = reg.list()
    if not items:
        rprint("[yellow]No projects yet. Run 'sanaa projects add'.[/yellow]")
        return None
    names = [p.name for p in items]
    rprint("[bold]Available projects:[/bold] " + ", ".join(names))
    name = safe_ask("Use project", default=reg.default or names[0])
    return reg.get(name)

# -------------------------
# conversational entrypoint
# -------------------------
@app.callback(invoke_without_command=True)
def root(ctx: typer.Context):
    if ctx.invoked_subcommand:
        return
    banner()
    rprint("What can I help with?")
    choice = safe_ask("Choose [chat/plan/code/debug/orchestrate/projects]", default="chat")
    # map to subcommand
    mapping = {"chat": chat, "plan": plan, "code": code, "debug": debug, "orchestrate": orchestrate, "projects": projects}
    cmd = mapping.get(choice)
    if cmd is None:
        rprint("[red]Unknown choice[/red]"); raise typer.Exit(1)
    ctx.invoke(cmd)

# -------------------------
# modes
# -------------------------
@app.command()
def chat(project: Optional[str] = typer.Option(None, "--project","-p", help="Project name")):
    reg = ProjectRegistry.load()
    proj = _pick_project(reg, project)
    system = {"role": "system", "content": "You are Sanaa, a helpful coding assistant."}
    messages: List[Dict[str, str]] = [system]
    if proj:
        messages.append({"role":"system","content": f"Project path: {proj.path}. Notes: {proj.notes or ''}"})
    rprint("[green]Type 'exit' to leave[/green]")
    while True:
        user = safe_ask("[bold magenta]you[/bold magenta]")
        messages.append({"role":"user","content": user})
        try:
            reply = _chat_once(messages)
        except httpx.HTTPError as e:
            rprint(f"[red]Model error: {e}[/red]")
            continue
        rprint(f"[cyan]sanaa[/cyan]: {reply}")
        messages.append({"role":"assistant","content": reply})

@app.command()
def plan(project: Optional[str] = typer.Option(None,"--project","-p")):
    reg = ProjectRegistry.load()
    proj = _pick_project(reg, project)
    goal = safe_ask("Describe your goal")
    ctx = f"Project {proj.name} at {proj.path}." if proj else "No project"
    prompt = f"Act as a software architect. {ctx} Create a step-by-step plan to: {goal}"
    out = _chat_once([{"role":"system","content":"Architect assistant."},{"role":"user","content":prompt}])
    console.rule("[bold]Plan[/bold]")
    rprint(out)

@app.command()
def code(project: Optional[str] = typer.Option(None,"--project","-p")):
    reg = ProjectRegistry.load()
    proj = _pick_project(reg, project)
    need = safe_ask("What should I implement?")
    ctx = f"Project path: {proj.path}" if proj else "No project"
    out = _chat_once([{"role":"system","content":"Senior Python engineer."},
                      {"role":"user","content":f"{ctx}\nWrite code to: {need}\nReturn clear diffs or new files."}])
    console.rule("[bold]Suggested changes[/bold]")
    rprint(out)

@app.command()
def debug(project: Optional[str] = typer.Option(None,"--project","-p")):
    """
    Smart debug:
      - If you paste a traceback, Sanaa analyzes it.
      - If you just hit Enter, Sanaa runs tests, captures failures, lints & type-checks,
        auto-finds impacted files/symbols, and surfaces docs for third-party APIs.
    """
    reg = ProjectRegistry.load()
    proj = _pick_project(reg, project)
    failure = safe_ask("Paste traceback / describe bug (or press Enter to auto-detect)", default="")
    report = auto_debug(proj.path if proj else ".", user_failure=failure or None)
    console.rule("[bold]Debug report[/bold]")
    rprint(summarize_fail_report(report))

@app.command()
def orchestrate(project: Optional[str] = typer.Option(None,"--project","-p"),
                goal: Optional[str] = typer.Argument(None)):
    reg = ProjectRegistry.load()
    proj = _pick_project(reg, project)
    if not goal:
        goal = safe_ask("What complex goal should I orchestrate?")
    ctx = f"Project {proj.name} at {proj.path}" if proj else "No project"
    out = _chat_once([{"role":"system","content":"You are an orchestrator that decomposes work."},
                      {"role":"user","content":f"{ctx}\nDecompose into tasks: {goal}"}])
    console.rule("[bold]Task graph[/bold]")
    rprint(out)

# -------------------------
# projects management
# -------------------------
projects = typer.Typer(help="Manage remembered projects")
app.add_typer(projects, name="projects")

@projects.command("list")
def projects_list():
    reg = ProjectRegistry.load()
    rows = [{"name": p.name, "path": p.path, "default": reg.default == p.name} for p in reg.list()]
    rprint(json.dumps(rows, indent=2))

@projects.command("add")
def projects_add():
    name = safe_ask("Project name")
    path = safe_ask("Path", default=str(Path.cwd()))
    model = safe_ask("Model id", default=DEFAULT_MODEL)
    notes = safe_ask("Notes", default="")
    fr = FileReader()
    # store a light index now; content is (re)read on demand
    index = [{"path": p, "size": len(txt)} for p, txt in fr.read(path).items()]
    proj = Project(name=name, path=path, model=model, notes=notes, files=index)
    reg = ProjectRegistry.load()
    reg.upsert(proj); reg.set_default(name); reg.save()
    # append journal entry
    reg.append_journal(name, {"event":"add_project","files_indexed":len(index)})
    rprint(f"[green]Saved project '{name}' with {len(index)} indexed files.[/green]")

@projects.command("scan")
def projects_scan(project: Optional[str] = typer.Option(None,"--project","-p")):
    reg = ProjectRegistry.load()
    proj = reg.get(_coerce_project_arg(project)) if project else _pick_project(reg, None)
    if not proj:
        raise typer.Exit(code=1)
    fr = FileReader()
    index = [{"path": p, "size": len(txt)} for p, txt in fr.read(proj.path).items()]
    proj.files = index; reg.upsert(proj); reg.save()
    reg.append_journal(proj.name, {"event":"rescan","files_indexed":len(index)})
    rprint(f"[green]Re-indexed {len(index)} files for '{proj.name}'.[/green]")
