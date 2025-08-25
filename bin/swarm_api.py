#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

ENV_FILE="/etc/coding-swarm/cswarm.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.strip().split('=',1)
                os.environ[k]=v.strip('"')

app = FastAPI(title="Coding Swarm API", version="2.0.0")

class RunRequest(BaseModel):
    goal: str
    project: str = "."
    model: Optional[str] = None
    dry_run: bool = False

@app.get("/health")
async def health():
    return {"status":"ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/info")
async def info():
    return {
        "service":"Coding Swarm API",
        "version":"2.0.0",
        "host": os.getenv("API_HOST","127.0.0.1"),
        "port": int(os.getenv("API_PORT","9100")),
    }

@app.post("/run")
async def run(req: RunRequest):
    proj = Path(req.project).resolve()
    if not proj.exists():
        raise HTTPException(400, "Project directory does not exist")
    return {"received": req.dict(), "ts": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1")
    port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
