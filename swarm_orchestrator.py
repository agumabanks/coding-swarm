#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, subprocess, pathlib, time, textwrap, shlex
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
import typer, yaml, requests

app = typer.Typer(add_completion=False)

def env(k, d=""):
    return os.getenv(k, d)

def run(cmd, cwd=None, timeout=600) -> tuple[int,str,str]:
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        p.kill(); return 124, "", "timeout"

def ts(): return datetime.utcnow().isoformat()

def openrouter_headers():
    # Works for OpenRouter/OpenAI-compatible APIs when OPENAI_BASE_URL + OPENAI_API_KEY set.
    h = {"Content-Type":"application/json"}
    if env("OPENAI_API_KEY"): h["Authorization"] = f"Bearer {env('OPENAI_API_KEY')}"
    return h

def chat(base_url, model, messages, max_tokens=2048, temperature=0.2):
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    r = requests.post(url, headers=openrouter_headers(), json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

def local_llama(messages):
    # llama.cpp server compatible route
    url = "http://127.0.0.1:8080/v1/chat/completions"
    payload = {"model":"local", "messages":messages, "max_tokens":2048, "temperature":0.2}
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def decide_provider(provider: str):
    provider = (provider or "local").lower()
    if provider == "local":
        return lambda msgs: local_llama(msgs), "local"
    base = env("OPENAI_BASE_URL", env("OPENROUTER_BASE_URL", "https://openrouter.ai/api"))
    model = env("OPENAI_MODEL", "gpt-4o")  # or your gpt-5 router
    return lambda msgs: chat(base, model, msgs), f"{base}:{model}"

def load_cfg(project: str):
    p = pathlib.Path(project) / "cswarm.yml"
    if p.exists():
        return yaml.safe_load(p.read_text()) or {}
    return {}

def add_memory(project: str, role: str, note: str):
    mdir = pathlib.Path(project)/".cswarm"; mdir.mkdir(exist_ok=True)
    with (mdir/"memory.jsonl").open("a") as f:
        f.write(json.dumps({"t":ts(),"role":role,"note":note})+"\n")

def doc_lookup(hints: List[str]) -> str:
    # Simple web search placeholder: you can later swap to Context7/OpenRouter tools.
    # Here we just format hints into a system preface.
    if not hints: return ""
    return "Relevant library topics:\n- " + "\n- ".join(hints) + "\n"

def stage_all_and_commit(msg: str) -> bool:
    code, out, err = run("git add -A && git diff --cached --quiet || git commit -m " + shlex.quote(msg))
    return code == 0

def maybe_push():
    if env("CSWARM_ALLOW_PUSH","0") == "1":
        run("git push --set-upstream origin $(git rev-parse --abbrev-ref HEAD)")

@app.command()
def orchestrate(goal: str = typer.Option(..., "--goal", "-g"),
                project: str = typer.Option(".", "--project", "-p"),
                provider: str = typer.Option("local", "--provider"),
                push: bool = typer.Option(False, "--push")):
    """
    Orchestrate: architect -> code -> test/build -> debug (auto-recover)
    """
    cfg = load_cfg(project)
    max_iters = int(cfg.get("max_iters", 3))
    test_cmd = cfg.get("test_cmd", "")
    build_cmd = cfg.get("build_cmd", "")
    personas = cfg.get("persona_prompts", {})
    doc_hints = cfg.get("doc_hints", [])
    memory_prelude = ""  # could load from .cswarm/memory.jsonl to prime the model

    call, ident = decide_provider(provider)
    typer.echo(f"[orchestrator] provider={ident}, max_iters={max_iters}")

    system_preface = doc_lookup(doc_hints) + (f"Goal: {goal}\n")
    add_memory(project, "system", f"Start goal: {goal}")

    for it in range(1, max_iters+1):
        typer.echo(f"\n== Iteration {it}/{max_iters} ==")

        # 1) Architect
        architect = personas.get("architect","Design the steps, files to change, and tests to run.")
        msgs = [
            {"role":"system","content": system_preface + "You are the Architect."},
            {"role":"user","content": f"{architect}\nProject root: {project}\nProduce a step plan and patch plan."}
        ]
        plan = call(msgs)
        add_memory(project,"architect",plan)
        (pathlib.Path(project)/".cswarm"/f"plan_{it}.md").write_text(plan)

        # 2) Coder – ask for a *minimal diff* patch (unified)
        coder = personas.get("coder","Apply the change as a unified diff. Keep it buildable.")
        msgs = [
            {"role":"system","content": system_preface + "You are the Coder. Return only a unified diff."},
            {"role":"user","content": f"{coder}\nWorking directory: {project}\nPlan:\n{plan}\nReturn a patch between ```diff fences."}
        ]
        diff_text = call(msgs)

        # extract and apply patch
        patch = []
        in_block = False
        for line in diff_text.splitlines():
            if line.strip().startswith("```") and "diff" in line:
                in_block = True; continue
            if line.strip().startswith("```") and in_block:
                break
            if in_block: patch.append(line)
        if patch:
            pfile = pathlib.Path(project)/".cswarm"/f"patch_{it}.diff"
            pfile.write_text("\n".join(patch)+"\n")
            code,out,err = run(f"git apply --whitespace=nowarn {pfile}", cwd=project)
            if code != 0:
                add_memory(project,"apply-fail",err)
                typer.echo(f"Patch failed to apply:\n{err}")
                # try reverse-context patch apply via 'git apply -R' if needed, else continue
                continue
            else:
                add_memory(project,"patch","applied")
        else:
            typer.echo("No diff block found; skipping apply.")

        # 3) Commit
        if stage_all_and_commit(f"[cswarm] iteration {it} for goal: {goal}"):
            typer.echo("Committed changes.")
        else:
            typer.echo("No staged changes; skipping commit.")

        # 4) Test/build
        status_ok = True
        logs = ""
        if test_cmd:
            code,out,err = run(test_cmd, cwd=project, timeout=900); logs += f"\n[TEST]\n{out}\n{err}"
            status_ok = status_ok and (code==0)
        if build_cmd:
            code,out,err = run(build_cmd, cwd=project, timeout=900); logs += f"\n[BUILD]\n{out}\n{err}"
            status_ok = status_ok and (code==0)
        (pathlib.Path(project)/".cswarm"/f"logs_{it}.txt").write_text(logs)

        if status_ok:
            typer.echo("Build/tests OK ✅")
            if push:
                os.environ["CSWARM_ALLOW_PUSH"]="1"
                maybe_push()
            break

        # 5) Debugger – feed error logs back for minimal fix
        debugger = personas.get("debugger","Given the logs, propose the smallest fix as unified diff.")
        msgs = [
            {"role":"system","content": system_preface + "You are the Debugger. Return only unified diff."},
            {"role":"user","content": f"{debugger}\nHere are the logs:\n{logs}\n"}
        ]
        fix = call(msgs)
        add_memory(project,"debugger",fix)

        # apply fix
        patch = []
        in_block = False
        for line in fix.splitlines():
            if line.strip().startswith("```") and "diff" in line:
                in_block = True; continue
            if line.strip().startswith("```") and in_block:
                break
            if in_block: patch.append(line)
        if patch:
            pfile = pathlib.Path(project)/".cswarm"/f"fix_{it}.diff"
            pfile.write_text("\n".join(patch)+"n")
            run(f"git apply --whitespace=nowarn {pfile}", cwd=project)
            stage_all_and_commit(f"[cswarm] fix iteration {it}")
        else:
            typer.echo("No fix patch found; continuing.")

    typer.echo("Done.")
