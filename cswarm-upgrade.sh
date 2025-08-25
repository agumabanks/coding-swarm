#!/usr/bin/env bash
# cswarm-upgrade.sh — add "swarmx" (Kilo-style modes + repo + chat + patching) on top of your stack
# - Installs a Python CLI (swarmx) with modes: architect/code/debug/orchestrate/ask
# - Clones repos, indexes structure, keeps project memory/journal, applies patches, branches/commits/pushes
# - Uses local llama.cpp server first; falls back to OpenRouter if configured
# - Integrates with your existing install layout under /opt/coding-swarm

set -euo pipefail

# ---------- Defaults ----------
ENV_FILE="${ENV_FILE:-/etc/coding-swarm/cswarm.env}"
BASE_DIR="${BASE_DIR:-/opt/coding-swarm}"
BIN_DIR="${BIN_DIR:-${BASE_DIR}/bin}"
VENV_DIR="${VENV_DIR:-${BASE_DIR}/venv}"
PROJECTS_DIR="${PROJECTS_DIR:-/home/swarm/projects}"

# local llama.cpp (OpenAI-like server) — your compose set these up on 8080..8083
LOCAL_OPENAI_URL_DEFAULT="http://127.0.0.1:8080/v1"
LOCAL_MODEL_DEFAULT="${LOCAL_MODEL_DEFAULT:-qwen2.5-coder-7b-instruct-q4_k_m}"

# OpenRouter fallback
OPENROUTER_BASE_DEFAULT="https://openrouter.ai/api/v1"

# ---------- Helpers ----------
ok(){ echo -e " \033[32m✓\033[0m $*"; }
warn(){ echo -e " \033[33m⚠\033[0m $*"; }
err(){ echo -e " \033[31m✗\033[0m $*"; exit 1; }
bar(){ local cur=$1 tot=$2; local w=40 f=$((cur*w/tot)) e=$((w-f)); printf "["; printf "%0.s█" $(seq 1 $f); printf "%0.s░" $(seq 1 $e); printf "]"; }

TOTAL=8; STEP=0
step(){ STEP=$((STEP+1)); printf "\n%s (%d/%d) %s\n" "$(bar $STEP $TOTAL)" "$STEP" "$TOTAL" "$1"; }

need_root(){
  if [[ $EUID -ne 0 ]]; then err "Run as root (sudo)."; fi
}

ensure_dirs(){
  mkdir -p "$BIN_DIR" "$PROJECTS_DIR"
  chown -R swarm:swarm "$PROJECTS_DIR" 2>/dev/null || true
}

write_env_defaults(){
  touch "$ENV_FILE"
  grep -q '^LOCAL_OPENAI_URL=' "$ENV_FILE" || echo "LOCAL_OPENAI_URL=\"$LOCAL_OPENAI_URL_DEFAULT\"" >> "$ENV_FILE"
  grep -q '^LOCAL_OPENAI_MODEL=' "$ENV_FILE" || echo "LOCAL_OPENAI_MODEL=\"$LOCAL_MODEL_DEFAULT\"" >> "$ENV_FILE"
  grep -q '^OPENROUTER_BASE=' "$ENV_FILE" || echo "OPENROUTER_BASE=\"$OPENROUTER_BASE_DEFAULT\"" >> "$ENV_FILE"
  # OPENROUTER_API_KEY can be added later by the user; don't force it.
}

install_python(){
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    ok "Created venv at $VENV_DIR"
  fi
  "$VENV_DIR/bin/pip" -q install --upgrade pip setuptools wheel
  "$VENV_DIR/bin/pip" -q install typer[all] rich httpx pydantic prompt_toolkit gitpython orjson
  ok "Python deps installed"
}

write_swarmx_py(){
  cat > "${BIN_DIR}/swarmx.py" <<'PY'
#!/usr/bin/env python3
# swarmx.py — Repo+Chat+Modes CLI (architect/code/debug/orchestrate/ask)
from __future__ import annotations
import os, sys, json, subprocess, textwrap, datetime, pathlib, re
from typing import List, Optional, Dict, Any
import httpx
import typer
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False, help="swarmx — repo + chat + patching + git, powered by local llama or OpenRouter fallback")
console = Console()

# --- config/env ---
ENV_FILE = os.environ.get("ENV_FILE", "/etc/coding-swarm/cswarm.env")
def load_env(path=ENV_FILE)->Dict[str,str]:
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v=line.split("=",1)
            env[k.strip()]=v.strip().strip('"')
    return env

ENV = load_env()
LOCAL_OPENAI_URL = os.environ.get("LOCAL_OPENAI_URL", ENV.get("LOCAL_OPENAI_URL","http://127.0.0.1:8080/v1"))
LOCAL_OPENAI_MODEL = os.environ.get("LOCAL_OPENAI_MODEL", ENV.get("LOCAL_OPENAI_MODEL","qwen2.5-coder-7b-instruct-q4_k_m"))
OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE", ENV.get("OPENROUTER_BASE","https://openrouter.ai/api/v1"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", ENV.get("OPENROUTER_API_KEY",""))

PROJECTS_DIR = os.environ.get("PROJECTS_DIR","/home/swarm/projects")

def project_paths(project:str)->Dict[str, pathlib.Path]:
    p = pathlib.Path(project).resolve()
    sw = p/".swarm"
    sw.mkdir(parents=True, exist_ok=True)
    return {
        "root": p,
        "swarm": sw,
        "journal": sw/"journal.md",
        "memory": sw/"memory.md",
        "index": sw/"index.txt",
        "history": sw/"history.jsonl",
        "patches": sw/"patches"
    }

# --- LLM client (local first, then OpenRouter) ---
class ChatMsg(BaseModel):
    role: str
    content: str

async def chat_completion(messages:List[ChatMsg], model_override:Optional[str]=None, temperature:float=0.2):
    headers = {"Content-Type":"application/json"}
    payload = {"model": model_override or LOCAL_OPENAI_MODEL, "messages":[m.model_dump() for m in messages], "temperature": temperature, "stream": False}
    # try local first
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{LOCAL_OPENAI_URL}/chat/completions" if not LOCAL_OPENAI_URL.endswith("/chat/completions") else LOCAL_OPENAI_URL, headers=headers, json=payload)
            if r.status_code==200:
                data = r.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        pass
    # fallback to OpenRouter if key present
    if OPENROUTER_API_KEY:
        headers.update({"Authorization": f"Bearer {OPENROUTER_API_KEY}", "HTTP-Referer":"https://server.local", "X-Title":"swarmx"})
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(f"{OPENROUTER_BASE}/chat/completions", headers=headers, json=payload)
                if r.status_code==200:
                    data = r.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text}")
        except Exception as e:
            raise RuntimeError(f"Local+OpenRouter both failed: {e}")
    raise RuntimeError("No local model response and no OPENROUTER_API_KEY set.")

# --- Prompts/modes (inspired by Kilo’s modes) ---
MODE_SYSTEM = {
    "ask": "You are a helpful engineer. Answer clearly. If code changes are required, propose a minimal diff as a unified patch.",
    "architect": "You are an architect. Propose an implementation design before coding. Output a concise plan and a follow-up patch if trivial.",
    "code": "You are a senior coder. Implement the requested change. Output a unified patch only. Use exact file paths from the repository root.",
    "debug": "You are a debugger. Diagnose failures and propose fixes. If a code edit is required, output a unified patch that can be applied with `git apply -p0`.",
    "orchestrate": "You are a project orchestrator. Break the goal into steps, delegate tasks, and end with a concrete unified patch for the highest-impact step."
}

PATCH_RE = re.compile(r'(?ms)^--- PATCH.*?^$', re.DOTALL)  # not used but reserved

def detect_patch(txt:str)->bool:
    return txt.lstrip().startswith("diff --git ")

def write_journal(paths:Dict[str,pathlib.Path], title:str, body:str):
    ts = datetime.datetime.utcnow().isoformat()
    with open(paths["journal"],"a") as f:
        f.write(f"\n## {ts} — {title}\n\n")
        f.write(body.strip()+"\n")

def write_history(paths:Dict[str,pathlib.Path], event:Dict[str,Any]):
    with open(paths["history"],"a") as f:
        f.write(json.dumps(event, ensure_ascii=False)+"\n")

def load_file_snippet(root:pathlib.Path, ref:str)->str:
    # ref like @src/app.ts or @README.md:1-60
    ref = ref.lstrip("@")
    path, rng = (ref.split(":",1)+[""])[:2]
    p = (root / path).resolve()
    if not p.is_file(): return f"[FILE-NOT-FOUND] {path}"
    content = p.read_text(errors="ignore")
    if rng:
        m = re.match(r"(\d+)-(\d+)$", rng)
        if m:
            a,b = int(m.group(1)), int(m.group(2))
            lines = content.splitlines()
            content = "\n".join(lines[a-1:b])
    return f"<<FILE:{path}>>\n{content}\n<<END:{path}>>"

def grep_docs(root:pathlib.Path, query:str, max_hits:int=6)->str:
    # a light "context7": scan common doc/code files for context
    candidates=[]
    exts=(".md",".txt",".ts",".tsx",".js",".py",".go",".rs",".java",".c",".cpp",".json",".yml",".yaml")
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and len(candidates)<2000:
            candidates.append(p)
    hits=[]
    q = re.compile(re.escape(query), re.I)
    for p in candidates:
        try:
            t=p.read_text(errors="ignore")
            if q.search(t):
                snippet="\n".join(t.splitlines()[:120])
                hits.append(f"### {p}\n{snippet}\n")
                if len(hits)>=max_hits: break
        except Exception:
            pass
    return "\n\n".join(hits) if hits else ""

def build_messages(mode:str, goal:str, root:pathlib.Path, chat_text:str, file_refs:List[str], memory_path:pathlib.Path)->List[ChatMsg]:
    sys_prompt = MODE_SYSTEM.get(mode, MODE_SYSTEM["ask"])
    files_blob = "\n\n".join(load_file_snippet(root, r) for r in file_refs) if file_refs else ""
    mem = memory_path.read_text() if memory_path.exists() else ""
    ctx = f"PROJECT_ROOT={root}\nMODE={mode}\nGOAL={goal}\nMEMORY:\n{mem}\nFILES:\n{files_blob}"
    user = f"{chat_text}\n"
    return [ChatMsg(role="system", content=sys_prompt+"\n"+ctx), ChatMsg(role="user", content=user)]

def apply_patch(project_root:pathlib.Path, patch_text:str)->bool:
    (project_root/".swarm/patches").mkdir(parents=True, exist_ok=True)
    patch_file = project_root/".swarm/patches"/(datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")+".patch")
    patch_file.write_text(patch_text)
    # try git apply
    proc = subprocess.run(["git","-C",str(project_root),"apply","-p0",str(patch_file)], capture_output=True, text=True)
    if proc.returncode==0:
        return True
    return False

def ensure_repo(project_root:pathlib.Path):
    if not (project_root/".git").exists():
        raise typer.BadParameter(f"{project_root} is not a git repository")

# ---------- Commands ----------
@app.command()
def repo(url:str, branch:Optional[str]=typer.Option(None), project_dir:Optional[str]=typer.Option(None, help="Where to clone (default /home/swarm/projects/<name>)")):
    """Clone a repository into the projects folder."""
    dest = pathlib.Path(project_dir) if project_dir else pathlib.Path(PROJECTS_DIR)/pathlib.Path(url).stem
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        console.print(f"[yellow]Dir exists, skipping clone: {dest}[/yellow]")
    else:
        subprocess.check_call(["git","clone","--depth","1", url, str(dest)])
        if branch:
            subprocess.check_call(["git","-C",str(dest),"checkout",branch])
    # write index and welcome journal
    paths = project_paths(str(dest))
    index = subprocess.run(["bash","-lc",f"cd {dest} && ls -laR"], capture_output=True, text=True).stdout
    paths["index"].write_text(index)
    if not paths["journal"].exists():
        paths["journal"].write_text(f"# Project Journal for {dest.name}\n")
    console.print(Panel.fit(f"Cloned to {dest}"))
    console.print("Run:  swarmx chat --project {dest}  (architect/code/debug/orchestrate/ask)")

@app.command()
def index(project:str):
    """Refresh the repository tree index (ls -R) into .swarm/index.txt"""
    paths = project_paths(project)
    out = subprocess.run(["bash","-lc",f"cd {paths['root']} && ls -laR"], capture_output=True, text=True).stdout
    paths["index"].write_text(out)
    console.print(Panel.fit("Index refreshed -> .swarm/index.txt"))

@app.command()
def commit(project:str, message:str=typer.Option(..., "--message","-m")):
    """Stage and commit."""
    ensure_repo(pathlib.Path(project))
    subprocess.check_call(["git","-C",project,"add","-A"])
    rc = subprocess.call(["git","-C",project,"diff","--cached","--quiet"])
    if rc==0:
        console.print("[yellow]No staged changes; skipping commit.[/yellow]")
        raise typer.Exit(0)
    subprocess.check_call(["git","-C",project,"commit","-m",message])
    console.print("[green]Committed.[/green]")

@app.command()
def push(project:str, remote:str="origin", branch:Optional[str]=None):
    """Push the current branch."""
    ensure_repo(pathlib.Path(project))
    if not branch:
        branch = subprocess.run(["git","-C",project,"rev-parse","--abbrev-ref","HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.check_call(["git","-C",project,"push",remote,branch])
    console.print(f"[green]Pushed {branch} to {remote}[/green]")

@app.command()
def task(
    goal:str = typer.Option(...,"--goal","-g"),
    project:str = typer.Option(...,"--project","-p"),
    mode:str = typer.Option("code","--mode",help="architect|code|debug|orchestrate|ask"),
    branch:str = typer.Option(None,"--branch", help="Create/switch to this branch"),
    auto_commit:bool = typer.Option(False, "--commit"),
    auto_push:bool = typer.Option(False, "--push"),
    model:str = typer.Option(None, "--model", help="Override model name")
):
    """Plan/patch/commit flow driven by LLM (mode decides style)."""
    paths = project_paths(project); root=paths["root"]
    ensure_repo(root)
    if branch:
        subprocess.call(["git","-C",str(root),"checkout","-B",branch])
    messages = build_messages(mode, goal, root, chat_text=goal, file_refs=[], memory_path=paths["memory"])
    import asyncio
    reply = asyncio.run(chat_completion(messages, model_override=model))
    write_journal(paths, f"task:{mode}", reply)
    if detect_patch(reply):
        ok = apply_patch(root, reply)
        console.print(Panel(f"Patch {'applied' if ok else 'FAILED to apply'}", title="swarmx"))
        if ok:
            subprocess.call(["git","-C",str(root),"status","--short"])
            if auto_commit:
                subprocess.call(["git","-C",str(root),"add","-A"])
                subprocess.call(["git","-C",str(root),"commit","-m",f"swarmx:{mode} - {goal}"])
                if auto_push:
                    push(str(root))
    else:
        console.print(Panel(reply, title=f"{mode} plan / notes"))

@app.command()
def chat(project:str, mode:str=typer.Option("ask","--mode"), model:str=typer.Option(None,"--model")):
    """Interactive chat with file references like @src/file.ts[:1-50]. Type 'exit' to quit."""
    paths = project_paths(project); root=paths["root"]
    console.print(Panel.fit(f"Chatting in [{mode}] mode — @file refs supported. 'exit' to quit."))
    while True:
        try:
            line = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print(); break
        if not line: continue
        if line.lower() in ("exit","quit"): break
        # collect @file refs
        refs = re.findall(r"@[\w\-/\.]+(?::\d+-\d+)?", line)
        messages = build_messages(mode, goal=line, root=root, chat_text=line, file_refs=refs, memory_path=paths["memory"])
        import asyncio
        try:
            reply = asyncio.run(chat_completion(messages, model_override=model))
        except Exception as e:
            console.print(f"[red]{e}[/red]"); continue
        print("\nassistant>\n"+reply+"\n")
        write_journal(paths, f"chat:{mode}", f"Q: {line}\n\nA:\n{reply}")
        # naive memory growth: append salient lines that look like decisions
        if "Decision:" in reply or "Summary:" in reply:
            with open(paths["memory"],"a") as f: f.write("\n"+reply+"\n")

@app.command()
def orchestrate(goal:str = typer.Option(...,"--goal","-g"), project:str=typer.Option(...,"--project","-p")):
    """Delegate to existing swarm_orchestrator.py run (keeps your earlier flow)."""
    orch = os.path.join(os.environ.get("BIN_DIR", "/opt/coding-swarm/bin"), "swarm_orchestrator.py")
    py = os.path.join(os.environ.get("VENV_DIR", "/opt/coding-swarm/venv"), "bin", "python")
    cmd = [py, orch, "run", "--goal", goal, "--project", project]
    subprocess.call(cmd)

if __name__=="__main__":
    app()
PY
  chmod +x "${BIN_DIR}/swarmx.py"
  ok "swarmx.py written"
}

write_wrapper(){
  cat > /usr/local/bin/swarmx <<EOF
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${ENV_FILE}"
if [[ -f "\$ENV_FILE" ]]; then set -a; source "\$ENV_FILE"; set +a; fi
VENV_DIR="${VENV_DIR}"
BIN_DIR="${BIN_DIR}"
exec "\$VENV_DIR/bin/python" "\$BIN_DIR/swarmx.py" "\$@"
EOF
  chmod +x /usr/local/bin/swarmx
  ok "Installed wrapper: /usr/local/bin/swarmx"
}

usage(){
  cat <<'USAGE'
swarmx — repo + chat + modes + patch/commit (local llama first, OpenRouter fallback)

Install:
  sudo bash cswarm-upgrade.sh install

Quick start:
  swarmx repo https://github.com/agumabanks/sanaa-website
  swarmx chat --project /home/swarm/projects/sanaa-website --mode architect
  swarmx task -g "Add a Contact page and route" -p /home/swarm/projects/sanaa-website --mode code --commit --push

Other:
  swarmx index   -p /path/to/project
  swarmx commit  -p /path/to/project -m "message"
  swarmx push    -p /path/to/project
  swarmx orchestrate -g "Refactor auth" -p /path/to/project    # calls your existing orchestrator

Env:
  LOCAL_OPENAI_URL=http://127.0.0.1:8080/v1
  LOCAL_OPENAI_MODEL=qwen2.5-coder-7b-instruct-q4_k_m
  OPENROUTER_BASE=https://openrouter.ai/api/v1
  OPENROUTER_API_KEY=sk-...

USAGE
}

cmd="${1:-}"
case "$cmd" in
  install)
    need_root; step "Create dirs"; ensure_dirs; ok "Dirs ok"
    step "Write env defaults"; write_env_defaults; ok "Env ok"
    step "Install Python deps"; install_python
    step "Write swarmx CLI"; write_swarmx_py
    step "Install wrapper"; write_wrapper
    step "Done"; ok "Use: swarmx --help"
    ;;
  *)
    usage
    ;;
esac
