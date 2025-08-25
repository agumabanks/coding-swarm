#!/usr/bin/env python3
from __future__ import annotations
import os, typer, time, logging, traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
audit_logger = logging.getLogger("cswarm.audit")
audit_logger.setLevel(logging.ERROR)
audit_logger.addHandler(logging.FileHandler(BASE_DIR / "audit.log"))

app = typer.Typer(add_completion=False, help="Coding Swarm Orchestrator (stub)")


def validate_project(p: str) -> Path:
    try:
        resolved = Path(p).resolve()
        resolved.relative_to(BASE_DIR)
        return resolved
    except Exception:
        audit_logger.error("invalid project", exc_info=True)
        typer.echo("Invalid project path", err=True)
        raise typer.Exit(1)


@app.command("run")
def run(goal: str = typer.Option(..., "--goal", "-g"), project: str = typer.Option(".", "--project", "-p"),
        model: str = typer.Option(os.getenv("OPENAI_MODEL", "gpt-5"), "--model"), dry_run: bool = typer.Option(False, "--dry-run")):
    proj = validate_project(project)
    try:
        print(f"[orchestrator] goal={goal} project={proj} model={model} dry_run={dry_run}")
        # TODO: queue, RAG, diff-apply; this stub returns immediately for health checks.
        time.sleep(1)
        print("[orchestrator] done.")
    except Exception:
        audit_logger.error("run failure", exc_info=True)
        typer.echo("Run failed; see audit log", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
