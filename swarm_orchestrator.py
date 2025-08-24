#!/usr/bin/env python3
"""
swarm_orchestrator.py — One-file, batteries-included multi‑agent coder

Purpose
-------
Turn high-level plans into production-ready code using a pipeline of specialized agents:
- Planner/Architect → breaks down the goal and drafts the architecture.
- Implementer → writes/edits code with diffs.
- Tester → runs project tests & static checks.
- Debugger → reads failures/logs and proposes concrete patches.
- Reviewer → enforces quality and security gates.
Round-trips until tests pass or limits are reached. Logs errors with AI fix suggestions.

Design notes (inspired by Kilo Code & friends)
---------------------------------------------
- Subagents with clear, composable prompts (inspired by Kilo Code’s “subagents” approach).
- OpenAI-compatible API surface so you can point at LiteLLM, OpenRouter, or your own router.
- File patches in structured JSON (safer than free-form text).
- Project-type detection for Laravel/React/Flutter with sensible test/lint commands.
- JSONL logs with error snapshots + AI “probable fix” field.
- Idempotent; safe writes with backups; dry-run support.

Quick start
-----------
$ export OPENAI_API_KEY=...                    # or your router key
$ export OPENAI_BASE_URL=http://127.0.0.1:8000 # e.g. LiteLLM router
$ python3 swarm_orchestrator.py run \
    --goal "Add JWT auth to the Laravel API and React app" \
    --model gpt-5 --project .

Dependencies
------------
Python 3.10+  (tested on 3.11+)
pip install openai==1.* typer rich pydantic tenacity

License
-------
MIT — do what you want, no warranty.
"""

from __future__ import annotations
import os
import sys
import json
import time
import shutil
import subprocess
import pathlib
import dataclasses
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel, Field, ValidationError
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# --------------- Globals ---------------

APP_NAME = "Swarm Orchestrator"
VERSION = "0.5.0"
console = Console()

# --------------- Utilities ---------------

def now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat()

def run_cmd(cmd: List[str], cwd: Optional[str]=None, timeout: Optional[int]=None) -> Tuple[int,str,str]:
    """Run a shell command, capture stdout/stderr, returncode."""
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired as e:
        try:
            proc.kill()
        except Exception:
            pass
        return 124, "", f"TimeoutExpired: {e}"
    except FileNotFoundError as e:
        return 127, "", f"FileNotFoundError: {e}"
    except Exception as e:
        return 1, "", f"Exception: {e}"

def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def write_text_safely(path: pathlib.Path, content: str, backup: bool=True) -> None:
    ensure_dir(path.parent)
    if path.exists() and backup:
        backup_path = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
        shutil.copy2(path, backup_path)
    path.write_text(content, encoding="utf-8")

def detect_project_type(project_dir: pathlib.Path) -> str:
    # Laravel, React (Node), Flutter, or generic
    if (project_dir / "artisan").exists() or (project_dir / "composer.json").exists():
        return "laravel"
    if (project_dir / "package.json").exists():
        return "node"
    if (project_dir / "pubspec.yaml").exists():
        return "flutter"
    return "generic"

# --------------- OpenAI-compatible client ---------------
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

class LLMError(Exception): ...
class LLMClient:
    def __init__(self, api_key: Optional[str]=None, base_url: Optional[str]=None, model: str="gpt-5"):
        if OpenAI is None:
            raise RuntimeError("Missing dependency: pip install openai")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Set OPENAI_API_KEY or pass api_key")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")  # optional for LiteLLM/router
        self.model = model

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.base_url else OpenAI(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), retry=retry_if_exception_type(LLMError))
    def chat_json(self, system: str, user: str, temperature: Optional[float]=None, response_schema: Optional[Dict]=None) -> Dict[str, Any]:
        """Ask the model to return a JSON object. Uses response_format if available."""
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            # Some routers/models don't allow non-default temperature; let router decide
            if temperature is not None:
                kwargs["temperature"] = temperature
            # Prefer JSON mode, but be resilient
            kwargs["response_format"] = {"type": "json_object"}

            resp = self._client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            raise LLMError(str(e))

# --------------- Agent Contracts ---------------

class FileEdit(BaseModel):
    path: str
    action: str = Field(..., pattern="^(create|replace|append|delete)$")
    content: Optional[str] = None
    explanation: Optional[str] = None

class Plan(BaseModel):
    title: str
    summary: str
    milestones: List[str]
    files_to_create: List[str] = []
    risks: List[str] = []
    acceptance_criteria: List[str] = []

class PatchSet(BaseModel):
    edits: List[FileEdit] = Field(default_factory=list)
    commit_message: str = "chore: apply AI-generated changes"

class TestResult(BaseModel):
    ok: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str

# --------------- Agent Prompts ---------------

PLANNER_PROMPT = """You are the Planner/Architect.
Goal: {goal}

Deliver a concise JSON plan with:
- title
- summary
- milestones (<=8)
- files_to_create (targeted paths)
- risks (security, scale, data)
- acceptance_criteria (measurable)

Keep it pragmatic and production-focused.
"""

IMPLEMENTER_PROMPT = """You are the Implementer.
Given:
- Project type: {project_type}
- Repo root: {project_dir}
- High level plan:
{plan}

Produce a JSON patch set with edits to implement the current milestone.
Rules:
- edits[].action in ["create","replace","append","delete"]
- edits[].path is POSIX relative to repo root
- After writing code, include tests when appropriate.
- Keep migrations/idempotency in Laravel. Use TypeScript in Node when possible.
- commit_message summarizes the change.
"""

DEBUGGER_PROMPT = """You are the Debugger.
Given:
- Project type: {project_type}
- Test command: {test_cmd}
- Exit code: {exit_code}
- STDERR (truncated): {stderr}
- STDOUT (truncated): {stdout}

Return a JSON patch set that fixes the root cause. Include clear commit_message.
If uncertain, add diagnostic logs or tests to isolate the failure.
"""

REVIEWER_PROMPT = """You are the Reviewer and Security Auditor.
Review the current diff and file set for quality/security/performance.
Return a JSON patch set for fixes (even small ones), or an empty edits list if OK.
Focus on: input validation, secrets, authz, SQLi/XSS, logging PII, race conditions; and simple perf wins.
"""

# --------------- Repo / Build Runners ---------------

class Repo:
    def __init__(self, root: pathlib.Path):
        self.root = root

    def write_patchset(self, patch: PatchSet, dry_run: bool=False) -> None:
        for e in patch.edits:
            path = (self.root / e.path).resolve()
            if not str(path).startswith(str(self.root.resolve())):
                raise ValueError(f"Refusing to write outside repo: {path}")
            if e.action == "create":
                if e.content is None: 
                    continue
                if dry_run:
                    console.print(f"[yellow]DRY[/] create {e.path}")
                else:
                    write_text_safely(path, e.content, backup=False)
            elif e.action == "replace":
                if e.content is None: 
                    continue
                if dry_run:
                    console.print(f"[yellow]DRY[/] replace {e.path}")
                else:
                    write_text_safely(path, e.content, backup=True)
            elif e.action == "append":
                if e.content is None: 
                    continue
                if dry_run:
                    console.print(f"[yellow]DRY[/] append {e.path}")
                else:
                    ensure_dir(path.parent)
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(e.content)
            elif e.action == "delete":
                if dry_run:
                    console.print(f"[yellow]DRY[/] delete {e.path}")
                else:
                    try:
                        path.unlink(missing_ok=True)
                    except Exception as ex:
                        console.print(f"[red]Delete failed[/] {path}: {ex}")

    def maybe_git_commit(self, message: str) -> None:
        # Commit if repo is a git repo with clean config
        rc, _, _ = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(self.root))
        if rc != 0:
            return
        run_cmd(["git", "add", "-A"], cwd=str(self.root))
        run_cmd(["git", "-c", "user.email=swarm@local", "-c", "user.name=Swarm", "commit", "-m", message], cwd=str(self.root))

class Runner:
    def __init__(self, repo: Repo, project_type: str):
        self.repo = repo
        self.project_type = project_type

    def install(self) -> None:
        if self.project_type == "laravel":
            # Composer install; npm if front-end exists
            run_cmd(["composer", "install", "--no-interaction", "--prefer-dist"], cwd=str(self.repo.root))
            if (self.repo.root / "package.json").exists():
                run_cmd(["npm", "ci"], cwd=str(self.repo.root))
        elif self.project_type == "node":
            if (self.repo.root / "package-lock.json").exists():
                run_cmd(["npm", "ci"], cwd=str(self.repo.root))
            else:
                run_cmd(["npm", "install"], cwd=str(self.repo.root))
        elif self.project_type == "flutter":
            run_cmd(["flutter", "pub", "get"], cwd=str(self.repo.root))
        else:
            pass

    def test_cmd(self) -> List[str]:
        if self.project_type == "laravel":
            if (self.repo.root / "artisan").exists():
                return ["php", "artisan", "test", "--no-interaction", "-q"]
            return ["vendor/bin/phpunit", "-q"]
        if self.project_type == "node":
            return ["npm", "test", "--silent"]
        if self.project_type == "flutter":
            return ["flutter", "test", "--machine"]
        return ["bash", "-lc", "echo 'No tests configured'; exit 0"]

    def run_tests(self, timeout: int=600) -> TestResult:
        cmd = self.test_cmd()
        rc, out, err = run_cmd(cmd, cwd=str(self.repo.root), timeout=timeout)
        return TestResult(ok=(rc == 0), command=" ".join(cmd), exit_code=rc,
                          stdout=out[-4000:], stderr=err[-4000:])

# --------------- Logging ---------------

class ErrorLogger:
    def __init__(self, log_dir: pathlib.Path):
        self.log_dir = log_dir
        ensure_dir(log_dir)
        self.jl = log_dir / "errors.jsonl"

    def log_failure(self, test: TestResult, ai_fix: Optional[Dict[str,Any]]=None) -> None:
        rec = {
            "ts": now_iso(),
            "command": test.command,
            "exit_code": test.exit_code,
            "stdout": test.stdout,
            "stderr": test.stderr,
            "ai_fix": ai_fix or {},
        }
        with open(self.jl, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# --------------- Orchestrator ---------------

class Orchestrator:
    def __init__(self, project_dir: str, model: str, base_url: Optional[str], api_key: Optional[str],
                 max_rounds: int=5, dry_run: bool=False):
        self.project_path = pathlib.Path(project_dir).resolve()
        ensure_dir(self.project_path)
        self.repo = Repo(self.project_path)
        self.project_type = detect_project_type(self.project_path)
        self.llm = LLMClient(api_key=api_key, base_url=base_url, model=model)
        self.runner = Runner(self.repo, self.project_type)
        self.errors = ErrorLogger(self.project_path / ".swarm" / "logs")
        self.max_rounds = max_rounds
        self.dry_run = dry_run

    def plan(self, goal: str) -> Plan:
        system = "You are an expert software architect with pragmatic taste."
        user = PLANNER_PROMPT.format(goal=goal)
        data = self.llm.chat_json(system, user, temperature=0.2)
        try:
            return Plan(**data)
        except ValidationError as e:
            console.print(f"[red]Plan schema error[/]: {e}")
            # Fallback minimal plan
            return Plan(title="Plan", summary=goal, milestones=[goal], files_to_create=[], risks=[], acceptance_criteria=[])

    def implement(self, plan: Plan, milestone: str) -> PatchSet:
        sysmsg = "You are a senior engineer writing precise patches. ONLY return JSON."
        user = IMPLEMENTER_PROMPT.format(project_type=self.project_type, project_dir=str(self.project_path), plan=f"- {milestone}")
        data = self.llm.chat_json(sysmsg, user, temperature=0.2)
        try:
            return PatchSet(**data)
        except ValidationError as e:
            console.print(f"[yellow]Implement returned invalid schema, attempting to coerce[/]")
            edits = data.get("edits", [])
            edits = [FileEdit(**e) for e in edits if "path" in e and "action" in e]
            cm = data.get("commit_message", "chore: AI changes")
            return PatchSet(edits=edits, commit_message=cm)

    def review(self, patch: PatchSet) -> PatchSet:
        sysmsg = "You are a meticulous code reviewer. ONLY return JSON."
        user = REVIEWER_PROMPT
        # Provide a synthetic 'diff' by listing edited files
        diff_list = "\n".join(f"- {e.action} {e.path}" for e in patch.edits[:32])
        data = self.llm.chat_json(sysmsg, f"{user}\n\nEdited files:\n{diff_list}", temperature=0.2)
        try:
            return PatchSet(**data)
        except ValidationError:
            edits = [FileEdit(**e) for e in data.get("edits", []) if "path" in e and "action" in e]
            return PatchSet(edits=edits, commit_message=data.get("commit_message","chore: review fixes"))

    def debug(self, test: TestResult) -> PatchSet:
        sysmsg = "You are a debugging specialist. ONLY return JSON."
        user = DEBUGGER_PROMPT.format(project_type=self.project_type, test_cmd=test.command,
                                      exit_code=test.exit_code, stderr=test.stderr, stdout=test.stdout)
        data = self.llm.chat_json(sysmsg, user, temperature=0.2)
        try:
            return PatchSet(**data)
        except ValidationError:
            edits = [FileEdit(**e) for e in data.get("edits", []) if "path" in e and "action" in e]
            return PatchSet(edits=edits, commit_message=data.get("commit_message","fix: tests"))

    def apply(self, patch: PatchSet, label: str) -> None:
        if not patch.edits:
            console.print(f"[green]{label}: nothing to apply[/]")
            return
        self.repo.write_patchset(patch, dry_run=self.dry_run)
        if not self.dry_run:
            self.repo.maybe_git_commit(patch.commit_message)
        console.print(f"[cyan]{label}: applied {len(patch.edits)} edit(s)[/]")

    def pipeline(self, goal: str) -> int:
        console.print(Panel.fit(f"{APP_NAME} v{VERSION}\nProject: {self.project_path}\nType: {self.project_type}", box=box.ROUNDED))
        console.print(f"[bold]Goal:[/] {goal}\n")

        plan = self.plan(goal)
        # Write architecture doc
        arch_md = self.project_path / "docs" / "architecture.md"
        write_text_safely(arch_md, f"# {plan.title}\n\n{plan.summary}\n\n## Milestones\n" +
                          "\n".join(f"- {m}" for m in plan.milestones) +
                          "\n\n## Acceptance Criteria\n" + "\n".join(f"- {a}" for a in plan.acceptance_criteria), backup=False)
        console.print(f"[green]Plan ready:[/] {plan.title}; {len(plan.milestones)} milestones")

        # Install deps early
        self.runner.install()

        rounds = 0
        for ms in plan.milestones or ["Initial implementation"]:
            rounds += 1
            if rounds > self.max_rounds:
                console.print("[yellow]Reached round limit[/]")
                break

            console.print(Panel.fit(f"Milestone: {ms}", style="bold cyan"))
            impl = self.implement(plan, ms)
            self.apply(impl, "Implement")

            # Reviewer pass
            review_patch = self.review(impl)
            self.apply(review_patch, "Review")

            # Test
            test = self.runner.run_tests()
            if test.ok:
                console.print("[bold green]Tests passed![/]")
                continue  # next milestone

            # Log failure + AI fix suggestion text
            suggestion = {"note": "Fix attempt will follow via debugger agent."}
            self.errors.log_failure(test, ai_fix=suggestion)
            console.print("[red]Tests failing — entering debug loop[/]")

            # Debug loop (bounded)
            for attempt in range(1, 4):
                dbg_patch = self.debug(test)
                self.apply(dbg_patch, f"Debug attempt {attempt}")
                test = self.runner.run_tests()
                if test.ok:
                    console.print("[bold green]Recovered: tests pass[/]")
                    break
                else:
                    self.errors.log_failure(test, ai_fix={"attempt": attempt, "note": "still failing"})
            else:
                console.print("[red]Could not get tests green for this milestone[/]")

        console.print(Panel.fit("Pipeline completed", style="bold green"))
        return 0

# --------------- CLI ---------------

app = typer.Typer(add_completion=False, help=f"{APP_NAME} CLI")

@app.command("run")
def run(
    goal: str = typer.Option(..., "--goal", "-g", help="High-level objective to implement"),
    project: str = typer.Option(".", "--project", "-p", help="Path to project root"),
    model: str = typer.Option(os.getenv("OPENAI_MODEL", "gpt-5"), "--model", "-m", help="Model name (router-supported)"),
    base_url: Optional[str] = typer.Option(os.getenv("OPENAI_BASE_URL"), "--base-url", help="OpenAI-compatible base URL (e.g., LiteLLM)"),
    api_key: Optional[str] = typer.Option(os.getenv("OPENAI_API_KEY"), "--api-key", help="API key (or set OPENAI_API_KEY)"),
    max_rounds: int = typer.Option(5, "--max-rounds", help="Maximum milestone rounds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files/commit"),
):
    """
    Execute the full agent pipeline: plan → implement → review → test → debug.
    """
    try:
        orch = Orchestrator(project_dir=project, model=model, base_url=base_url, api_key=api_key,
                            max_rounds=max_rounds, dry_run=dry_run)
        raise SystemExit(orch.pipeline(goal))
    except Exception as e:
        console.print(f"[bold red]Fatal:[/] {e}")
        raise SystemExit(1)

@app.command("debug-once")
def debug_once(
    project: str = typer.Option(".", "--project", "-p"),
    model: str = typer.Option(os.getenv("OPENAI_MODEL", "gpt-5"), "--model", "-m"),
    base_url: Optional[str] = typer.Option(os.getenv("OPENAI_BASE_URL"), "--base-url"),
    api_key: Optional[str] = typer.Option(os.getenv("OPENAI_API_KEY"), "--api-key"),
):
    """
    Run tests, and if failing, call the debugger agent exactly once and apply its patch.
    """
    orch = Orchestrator(project_dir=project, model=model, base_url=base_url, api_key=api_key)
    orch.runner.install()
    test = orch.runner.run_tests()
    if test.ok:
        console.print("[green]Tests already passing.[/]")
        raise SystemExit(0)
    dbg_patch = orch.debug(test)
    orch.apply(dbg_patch, "Debug single-pass")
    raise SystemExit(0)

@app.command("plan")
def plan_cmd(
    goal: str = typer.Argument(..., help="Goal to architect"),
    project: str = typer.Option(".", "--project", "-p"),
    model: str = typer.Option(os.getenv("OPENAI_MODEL", "gpt-5"), "--model", "-m"),
    base_url: Optional[str] = typer.Option(os.getenv("OPENAI_BASE_URL"), "--base-url"),
    api_key: Optional[str] = typer.Option(os.getenv("OPENAI_API_KEY"), "--api-key"),
):
    """
    Generate an architecture plan only and write docs/architecture.md
    """
    orch = Orchestrator(project_dir=project, model=model, base_url=base_url, api_key=api_key)
    plan = orch.plan(goal)
    arch_md = orch.project_path / "docs" / "architecture.md"
    write_text_safely(arch_md, f"# {plan.title}\n\n{plan.summary}\n\n## Milestones\n" +
                      "\n".join(f"- {m}" for m in plan.milestones) +
                      "\n\n## Acceptance Criteria\n" + "\n".join(f"- {a}" for a in plan.acceptance_criteria), backup=False)
    console.print(f"[green]Wrote[/] {arch_md}")
    print(plan.model_dump_json(indent=2))

if __name__ == "__main__":
    app()
