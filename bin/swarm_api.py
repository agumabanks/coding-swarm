#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

ENV_FILE = "/etc/coding-swarm/cswarm.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=',1)
                os.environ[k] = v.strip('"')

VENV = os.getenv("VENV_DIR","/opt/coding-swarm/venv") + "/bin/python"
ORCH = os.getenv("BIN_DIR","/opt/coding-swarm/bin") + "/swarm_orchestrator.py"

app = FastAPI(title="Coding Swarm API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_headers=["*"], allow_methods=["*"])

class RunRequest(BaseModel):
    goal: str
    project: str = "."
    model: Optional[str] = None
    dry_run: bool = False

@app.get("/health")
def health(): return {"status":"ok","timestamp":datetime.utcnow().isoformat()}

@app.get("/info")
def info():
    return {"service":"Coding Swarm API","version":"2.0.0","host": os.getenv("NGINX_SERVER_NAME","")}

@app.post("/run")
def run_orchestrator(req: RunRequest):
    p = Path(req.project).resolve()
    if not p.exists(): raise HTTPException(400, "Project dir not found")
    cmd=[VENV, ORCH, "run", "--goal", req.goal, "--project", str(p)]
    if req.model: cmd += ["--model", req.model]
    if req.dry_run: cmd += ["--dry-run"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {"status":"ok" if out.returncode==0 else "fail","exit_code":out.returncode,"stdout":out.stdout,"stderr":out.stderr}
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "timeout")
if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1"); port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
