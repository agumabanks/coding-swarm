#!/usr/bin/env bash
# sanaa-all.sh — install/upgrade + syscheck + minimal repair + real orchestrator
# Makes `sanaa` a global CLI that can: clone, index, chat, run tasks, commit & push.

set -euo pipefail

# ---------- Paths / defaults ----------
ROOT_DIR="/opt/coding-swarm"
BIN_DIR="${ROOT_DIR}/bin"
VENV_DIR="${ROOT_DIR}/venv"
ETC_DIR="/etc/coding-swarm"
ENV_FILE="${ETC_DIR}/cswarm.env"
SWARM_USER="swarm"

# Default to local llama.cpp(OpenAI-compatible) server at :8080
DEFAULT_OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
DEFAULT_OPENAI_MODEL="${OPENAI_MODEL:-qwen2.5-coder-7b-instruct-q4_k_m.gguf}"

# ---------- tiny ui ----------
bar(){ local c=$1 t=$2 w=36; local f=$(( c*w/t )); printf "["; printf "%0.s█" $(seq 1 $f); printf "%0.s░" $(seq $((f+1)) $w); printf "]"; }
ok(){  printf " \033[32m✓ %s\033[0m\n" "$*"; }
warn(){ printf " \033[33m⚠ %s\033[0m\n" "$*"; }
info(){ printf " \033[36mℹ %s\033[0m\n" "$*"; }
die(){ printf " \033[31m✗ %s\033[0m\n" "$*"; exit 1; }

need_root(){ [[ $EUID -eq 0 ]] || die "Run with sudo/root"; }

ensure_dirs(){
  mkdir -p "$BIN_DIR" "$ETC_DIR"
  id -u "$SWARM_USER" &>/dev/null || useradd -m -s /bin/bash "$SWARM_USER"
  chown -R "$SWARM_USER:$SWARM_USER" "$ROOT_DIR" || true
}

write_env_defaults(){
  touch "$ENV_FILE"
  grep -q '^OPENAI_BASE_URL=' "$ENV_FILE" 2>/dev/null || echo "OPENAI_BASE_URL=\"${DEFAULT_OPENAI_BASE_URL}\"" >> "$ENV_FILE"
  grep -q '^OPENAI_MODEL='    "$ENV_FILE" 2>/dev/null || echo "OPENAI_MODEL=\"${DEFAULT_OPENAI_MODEL}\"" >> "$ENV_FILE"
  # Keep API_PORT sane if present (avoid earlier bad quote/braces)
  if grep -q '^API_PORT=' "$ENV_FILE"; then sed -i 's/^API_PORT=.*/API_PORT="9101"/' "$ENV_FILE"; fi
  ok "ENV ready → $ENV_FILE"
}

ensure_deps(){
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip git curl jq
  ok "OS deps ok"
}

ensure_venv(){
  if [[ ! -d "$VENV_DIR" ]]; then python3 -m venv "$VENV_DIR"; fi
  "$VENV_DIR/bin/pip" -q install --upgrade pip setuptools wheel
  "$VENV_DIR/bin/pip" -q install typer==0.12.* rich==13.* httpx==0.27.* pydantic==2.* tenacity==8.* \
                       prompt_toolkit==3.* orjson==3.* gitpython==3.* pygments==2.*
  ok "Python deps ok"
}

write_orchestrator(){
  local PY="${BIN_DIR}/sanaa_orchestrator.py"
  cat > "$PY" <<'PYCODE'
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
import httpx
from dataclasses import dataclass

console = Console()
app = typer.Typer(add_completion=False)

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "sk-local")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "qwen2.5-coder-7b-instruct-q4_k_m.gguf")

IGNORE_DIRS = {".git","node_modules",".venv","__pycache__","dist","build",".next",".svelte-kit",".turbo"}
TEXT_EXT = {".txt",".md",".py",".ts",".tsx",".js",".jsx",".json",".yaml",".yml",".toml",".html",".css",".scss",".rs",".go",".java",".kt",".swift",".php",".rb",".c",".h",".cpp",".cc",".cs",".sql",".env",".sh"}

def _client():
    headers={"Authorization": f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"}
    # Some servers want /v1 prefix present in base URL, some want path in request — we handle both.
    base = OPENAI_BASE_URL.rstrip("/")
    path = "/chat/completions" if base.endswith("/v1") else "/v1/chat/completions"
    return base, path, headers

def chat_once(messages: list[dict], temperature: float=0.2, max_tokens: int=2048) -> str:
    base, path, headers = _client()
    payload={"model": OPENAI_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    with httpx.Client(timeout=120.0) as c:
        r=c.post(base+path, json=payload, headers=headers)
        r.raise_for_status()
        data=r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data, indent=2)

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
PYCODE
  chmod +x "$PY"
  chown "$SWARM_USER:$SWARM_USER" "$PY" || true
  ok "Orchestrator written → $PY"
}

write_cli(){
  # launcher that sources env (if present) and execs python — no loops, no noisy notices
  cat > /usr/local/bin/sanaa <<EOF
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${ENV_FILE:-$ENV_FILE}"
if [[ -f "\$ENV_FILE" ]]; then set -a; source "\$ENV_FILE"; set +a; fi
exec "$VENV_DIR/bin/python" "$BIN_DIR/sanaa_orchestrator.py" "\$@"
EOF
  chmod +x /usr/local/bin/sanaa
  ln -sf /usr/local/bin/sanaa /usr/local/bin/sanaa.ai
  ok "CLI installed → /usr/local/bin/sanaa (alias: sanaa.ai)"
}

syscheck(){
  echo "== Sanaa Syscheck =="
  echo "-- which sanaa"; which sanaa || true
  echo "-- ENV"; [[ -f "$ENV_FILE" ]] && sed -n '1,50p' "$ENV_FILE" || echo "(no env)"
  echo "-- local llama health (8080):"; curl -fsS http://127.0.0.1:8080/health || echo "no /health (ok for some builds)"
  echo "-- help"; sanaa --help | head -n 15 || true
}

repair(){
  # Currently nothing fancy; re-write launcher to be safe & re-pin env defaults
  write_env_defaults
  write_cli
  ok "Repaired launcher/env"
}

install_all(){
  need_root
  ensure_dirs
  step=0; total=6
  step=$((step+1)); printf "%s (1/%d) deps\n" "$(bar $step $total)" "$total"; ensure_deps
  step=$((step+1)); printf "%s (2/%d) env\n"  "$(bar $step $total)" "$total"; write_env_defaults
  step=$((step+1)); printf "%s (3/%d) venv\n" "$(bar $step $total)" "$total"; ensure_venv
  step=$((step+1)); printf "%s (4/%d) orchestrator\n" "$(bar $step $total)" "$total"; write_orchestrator
  step=$((step+1)); printf "%s (5/%d) cli\n"  "$(bar $step $total)" "$total"; write_cli
  step=$((step+1)); printf "%s (6/%d) syscheck\n" "$(bar $step $total)" "$total"; syscheck
  echo; ok "Install complete. Try:"
  echo "  sanaa repo https://github.com/agumabanks/sanaa-website --project /home/swarm/projects/sanaa-website"
  echo "  sanaa chat --project /home/swarm/projects/sanaa-website --mode debug"
  echo "  sanaa task \"Add a basic contact form\" --project /home/swarm/projects/sanaa-website --mode code --commit"
}

usage(){
  cat <<USAGE
Usage:
  sudo $0 install         # install/upgrade Sanaa CLI + orchestrator
  sudo $0 syscheck        # quick health checks
  sudo $0 repair          # rewrite launcher/env defaults

Examples:
  sanaa repo https://github.com/agumabanks/sanaa-website --project /home/swarm/projects/sanaa-website
  sanaa chat --project /home/swarm/projects/sanaa-website --mode debug
  sanaa task "Fix build" --project /home/swarm/projects/sanaa-website --mode code --commit --push
  sanaa --goal "Add auth" --project /home/swarm/projects/sanaa-website
USAGE
}

case "${1:-}" in
  install) install_all;;
  syscheck) syscheck;;
  repair) repair;;
  *) usage; exit 0;;
esac
