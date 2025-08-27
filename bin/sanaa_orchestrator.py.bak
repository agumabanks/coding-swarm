#!/usr/bin/env python3
"""
sanaa_orchestrator.py — Sanaa task runner

Modes:
 - repo <git_url> [--project PATH]         -> clone into PATH (default /home/swarm/projects/<name>)
 - index --project PATH                    -> build .sanaa/index.json + short summary
 - chat  --project PATH [--mode ...]       -> interactive chat (supports @relative/file.ext mentions)
 - task  "goal" --project PATH [--mode ...] [--commit] [--push] [--branch BR]
 - run   --goal "..." --project PATH       -> compatibility with old `sanaa --goal ...`

Local defaults: OPENAI_BASE_URL=http://127.0.0.1:8080/v1 (llama.cpp / OpenAI-compatible),
                OPENAI_MODEL=qwen2.5-coder-7b-instruct-q4_k_m.gguf
"""
from __future__ import annotations
import os, sys, json, time, subprocess, hashlib, textwrap, re, shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from dataclasses import dataclass

from api.providers import BaseProvider, get_provider

console = Console()
app = typer.Typer(add_completion=False)

provider: BaseProvider

IGNORE_DIRS = {".git","node_modules",".venv","__pycache__","dist","build",".next",".svelte-kit",".turbo"}
TEXT_EXT = {".txt",".md",".py",".ts",".tsx",".js",".jsx",".json",".yaml",".yml",".toml",".html",".css",".scss",".rs",".go",".java",".kt",".swift",".php",".rb",".c",".h",".cpp",".cc",".cs",".sql",".env",".sh"}


@app.callback()
def _main(
    provider_name: str = typer.Option(
        os.getenv("CSWARM_PROVIDER", "openai-compatible"),
        "--provider",
        help="LLM provider to use",
    ),
) -> None:
    """Initialize global provider from CLI or env."""
    global provider
    provider = get_provider(provider_name)

def chat_once(messages: list[dict], temperature: float=0.2, max_tokens: int=2048) -> str:
    return provider.chat(messages, temperature=temperature, max_tokens=max_tokens)

def sha1(s:str)->str: return hashlib.sha1(s.encode()).hexdigest()[:8]

def ensure_project_dir(project: Path)->Path:
    p=project.resolve()
    if not p.exists(): p.mkdir(parents=True, exist_ok=True)
    return p

def files_listing(root: Path) -> list[dict]:
    rows=[]
    for p in root.rglob("*"):
        rel=p.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts): continue
        if p.is_file(): rows.append({"path": str(rel), "size": p.stat().st_size})
    return rows

def read_rel(project: Path, rel: str) -> str:
    p=(project/rel).resolve()
    if project not in p.parents and p!=project:  # prevent path escape
        return f"[security] Skipped out-of-tree path: {rel}"
    try:
        if p.suffix.lower() in TEXT_EXT and p.stat().st_size < 400_000:
            return p.read_text(errors="ignore")
        else:
            return f"[non-text or large file: {rel} ({p.stat().st_size} bytes)]"
    except Exception as e:
        return f"[read error {rel}: {e}]"

def journal_append(project: Path, text: str):
    (project/".sanaa").mkdir(exist_ok=True)
    j=project/".sanaa"/"journal.md"
    with j.open("a", encoding="utf-8") as f:
        f.write(f"\n\n### {time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n{text}\n")

def index_build(project: Path) -> dict:
    rows=files_listing(project)
    info={"project": str(project), "count": len(rows), "files": rows}
    (project/".sanaa").mkdir(exist_ok=True)
    (project/".sanaa"/"index.json").write_text(json.dumps(info, indent=2))
    return info

def git(cmd:list[str], cwd:Path)->subprocess.CompletedProcess:
    return subprocess.run(["git"]+cmd, cwd=str(cwd), text=True, capture_output=True)

def ensure_git(project: Path):
    if not (project/".git").exists():
        r=git(["init"], project); assert r.returncode==0, r.stderr

# -------- Commands --------

@app.command("repo")
def repo_clone(
    git_url: str = typer.Argument(..., help="Git URL to clone"),
    project: Optional[Path] = typer.Option(None, "--project","-p", help="Target path"),
):
    """
    Clone a repository to PATH (defaults to /home/swarm/projects/<reponame>)
    """
    if project is None:
        name=git_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"): name=name[:-4]
        project=Path(f"/home/swarm/projects/{name}")
    project=ensure_project_dir(project)
    if any(project.iterdir()):
        console.print(f"[yellow]Target {project} not empty; skipping clone.[/yellow]")
    else:
        project.parent.mkdir(parents=True, exist_ok=True)
        r=subprocess.run(["git","clone",git_url,str(project)], text=True)
        if r.returncode!=0: raise typer.Exit(code=r.returncode)
    index_build(project)
    console.print(Panel.fit(f"Repo ready at [bold]{project}[/bold]", title="sanaa repo"))

@app.command("index")
def index_cmd(project: Path=typer.Option(...,"--project","-p")):
    info=index_build(project)
    table=Table(title="Project index")
    table.add_column("files"); table.add_column("first 5")
    sample=[f["path"] for f in info["files"][:5]]
    table.add_row(str(info["count"]), "\n".join(sample))
    console.print(table)

@app.command("chat")
def chat_cmd(
    project: Path=typer.Option(...,"--project","-p"),
    mode: str=typer.Option("debug","--mode", help="architect|code|debug|orchestrator"),
):
    """
    Interactive chat. Mention files like @src/file.ts to include their content.
    """
    project=project.resolve()
    console.print(Panel.fit(f"Chatting on [bold]{project}[/bold] (mode={mode})", title="sanaa chat"))
    console.print("[dim]Type 'exit' to quit.[/dim]")
    sys_prompt=f"You are Sanaa in {mode} mode. Be concise, propose diffs when coding. If user mentions @file, use its contents."

    while True:
        try:
            q=input("\nYou> ")
        except (EOFError, KeyboardInterrupt):
            print(); break
        if q.strip().lower() in {"exit","quit"}: break

        # collect @file mentions
        addins=[]
        for m in re.findall(r"@([\w./-]+)", q):
            addins.append({"file": m, "content": read_rel(project, m)})

        messages=[{"role":"system","content":sys_prompt},
                  {"role":"user","content":json.dumps({"question":q,"context":addins})}]
        ans=chat_once(messages)
        journal_append(project, f"**Q**: {q}\n\n**A**:\n\n{ans}")
        console.print(Markdown(ans))

@app.command("task")
def task_cmd(
    goal: str=typer.Argument(..., help="What to do"),
    project: Path=typer.Option(...,"--project","-p"),
    mode: str=typer.Option("code","--mode"),
    commit: bool=typer.Option(False,"--commit"),
    push: bool=typer.Option(False,"--push"),
    branch: Optional[str]=typer.Option(None,"--branch"),
):
    """
    Run a one-shot task on a repo. The LLM proposes patches (unified diff).
    We apply simple diffs that only touch text files already present.
    """
    project=project.resolve()
    ensure_git(project)
    if branch:
        git(["checkout","-B",branch], project)

    sys_prompt=f"""You are Sanaa in {mode} mode.
Given the repository tree (partial) and the GOAL, return a unified diff patch (git-style) that applies cleanly.
Only change existing text files. No shell commands. If no change needed, reply 'NOOP'.
"""
    tree = "\n".join([f["path"] for f in files_listing(project)[:500]])
    user = {"goal": goal, "tree": tree}
    messages=[{"role":"system","content":sys_prompt},
              {"role":"user","content":json.dumps(user)}]
    ans=chat_once(messages, max_tokens=2048)

    (project/".sanaa").mkdir(exist_ok=True)
    (project/".sanaa"/"last_patch.diff").write_text(ans)
    journal_append(project, f"**GOAL**: {goal}\n\n**PATCH**:\n\n```\n{ans}\n```")

    if ans.strip().upper().startswith("NOOP"):
        console.print("[yellow]LLM says NOOP[/yellow]"); raise typer.Exit()

    # Very simple patch apply attempt
    patch=(project/".sanaa"/"last_patch.diff")
    res=subprocess.run(["git","apply","--index",str(patch)], cwd=str(project), text=True, capture_output=True)
    if res.returncode!=0:
        console.print("[red]Patch failed[/red]\n"+res.stderr); raise typer.Exit(code=1)

    if commit:
        msg=f"sanaa: {mode} – {goal[:72]}"
        git(["commit","-m",msg], project)
        console.print(f"[green]Committed:[/green] {msg}")
        if push:
            git(["push","-u","origin", branch or "sanaa/auto-"+sha1(goal)], project)

    console.print(Panel.fit("Task done", title="sanaa"))

# Compatibility with `sanaa --goal ...`
@app.command("run")
def run(goal: str=typer.Option(...,"--goal","-g"), project: Path=typer.Option(".","--project","-p"),
        model: Optional[str]=typer.Option(None,"--model"), dry_run: bool=typer.Option(False,"--dry-run")):
    global OPENAI_MODEL
    if model: OPENAI_MODEL=model
    console.print(f"[dim][orchestrator] goal={goal} project={project} model={OPENAI_MODEL} dry_run={dry_run}[/dim]")
    if dry_run:
        console.print("dry-run, exiting"); return
    # Delegate to task (code mode by default) without commit/push
    task_cmd.callback(goal=goal, project=project, mode="code", commit=False, push=False, branch=None)

def main():
    # If called as: sanaa --goal ... (no subcommand), force 'run'
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        sys.argv.insert(1,"run")
    app()

if __name__ == "__main__":
    main()
