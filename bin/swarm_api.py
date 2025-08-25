#!/usr/bin/env python3
import os, subprocess, logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import traceback

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).resolve().parents[1]
AUDIT_LOG = BASE_DIR / "audit.log"

audit_logger = logging.getLogger("cswarm.audit")
audit_logger.setLevel(logging.ERROR)
_fh = logging.FileHandler(AUDIT_LOG)
audit_logger.addHandler(_fh)


def sanitize_output(text: str) -> str:
    """Remove absolute paths and other sensitive info from outputs."""
    return text.replace(str(BASE_DIR), "<workspace>")


def validate_path(p: str) -> Path:
    """Ensure path is within workspace and exists."""
    try:
        resolved = Path(p).resolve()
        resolved.relative_to(BASE_DIR)
        return resolved
    except Exception:
        raise HTTPException(400, "Invalid project path")

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
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/info")
async def info():
    return {
        "service": "Coding Swarm API",
        "version": "2.0.0",
        "host": os.getenv("API_HOST", "127.0.0.1"),
        "port": int(os.getenv("API_PORT", "9100")),
    }

@app.post("/run")
async def run(req: RunRequest):
    try:
        proj = validate_path(req.project)
        if not proj.exists():
            raise HTTPException(404, "Project directory does not exist")
        data = {
            "goal": req.goal,
            "project": str(proj.relative_to(BASE_DIR)),
            "model": req.model,
            "dry_run": req.dry_run,
        }
        return {"received": data, "ts": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception:
        audit_logger.error("run failed", exc_info=True)
        raise HTTPException(500, "Internal server error")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(sanitize_output(msg))
    except Exception:
        audit_logger.error("websocket error", exc_info=True)
        await ws.close()

if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1")
    port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
