#!/usr/bin/env python3
# <<<<<<< codex/validate-file-paths-and-command-inputs
# import os, subprocess, logging
# from pathlib import Path
# from datetime import datetime
# from typing import Optional
# import traceback
# =======
import os, asyncio, uuid, time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from collections import deque
# >>>>>>> main

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

MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "5"))
DEFAULT_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "900"))

request_times = deque()
pending_tasks: Dict[str, Dict] = {}
running_tasks: Dict[str, asyncio.Task] = {}
completed_tasks: Dict[str, Dict] = {}
task_queue: asyncio.Queue[str] = asyncio.Queue()
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

app = FastAPI(title="Coding Swarm API", version="2.0.0")

class RunRequest(BaseModel):
    goal: str
    project: str = "."
    model: Optional[str] = None
    dry_run: bool = False
    timeout: Optional[int] = None


async def worker():
    while True:
        task_id = await task_queue.get()
        info = pending_tasks.pop(task_id, None)
        if not info:
            continue  # cancelled before start
        await semaphore.acquire()
        running_tasks[task_id] = asyncio.create_task(execute(task_id, info))


async def execute(task_id: str, info: Dict):
    cmd = [
        "python3",
        str(Path(__file__).with_name("swarm_orchestrator.py")),
        "run",
        "--goal",
        info["goal"],
        "--project",
        info["project"],
    ]
    if info.get("model"):
        cmd.extend(["--model", info["model"]])
    if info.get("dry_run"):
        cmd.append("--dry-run")

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    timeout = info.get("timeout") or DEFAULT_TIMEOUT
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        completed_tasks[task_id] = {
            "status": "completed",
            "returncode": proc.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        completed_tasks[task_id] = {"status": "timeout"}
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        completed_tasks[task_id] = {"status": "cancelled"}
        raise
    finally:
        running_tasks.pop(task_id, None)
        semaphore.release()


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(worker())

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
# <<<<<<< codex/validate-file-paths-and-command-inputs
#     try:
#         proj = validate_path(req.project)
#         if not proj.exists():
#             raise HTTPException(404, "Project directory does not exist")
#         data = {
#             "goal": req.goal,
#             "project": str(proj.relative_to(BASE_DIR)),
#             "model": req.model,
#             "dry_run": req.dry_run,
#         }
#         return {"received": data, "ts": datetime.utcnow().isoformat()}
#     except HTTPException:
#         raise
#     except Exception:
#         audit_logger.error("run failed", exc_info=True)
#         raise HTTPException(500, "Internal server error")


# @app.websocket("/ws")
# async def websocket_endpoint(ws: WebSocket):
#     await ws.accept()
#     try:
#         while True:
#             msg = await ws.receive_text()
#             await ws.send_text(sanitize_output(msg))
#     except Exception:
#         audit_logger.error("websocket error", exc_info=True)
#         await ws.close()
# =======
    proj = Path(req.project).resolve()
    if not proj.exists():
        raise HTTPException(400, "Project directory does not exist")
    now = time.time()
    while request_times and now - request_times[0] > 60:
        request_times.popleft()
    if len(request_times) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Too many requests")
    request_times.append(now)
    task_id = uuid.uuid4().hex
    pending_tasks[task_id] = {
        "goal": req.goal,
        "project": str(proj),
        "model": req.model,
        "dry_run": req.dry_run,
        "timeout": req.timeout,
    }
    await task_queue.put(task_id)
    return {"task_id": task_id, "status": "queued"}


@app.get("/queue/status")
async def queue_status():
    return {
        "running": {
            "ids": list(running_tasks.keys()),
            "count": len(running_tasks),
        },
        "pending": {
            "ids": list(pending_tasks.keys()),
            "count": len(pending_tasks),
        },
        "completed": {
            "ids": list(completed_tasks.keys()),
            "count": len(completed_tasks),
        },
    }


@app.delete("/queue/{task_id}")
async def cancel_task(task_id: str):
    if task_id in pending_tasks:
        pending_tasks.pop(task_id, None)
        return {"status": "cancelled"}
    if task_id in running_tasks:
        running_tasks[task_id].cancel()
        return {"status": "cancelling"}
    if task_id in completed_tasks:
        return {"status": "completed"}
    raise HTTPException(404, "Task not found")
# >>>>>>> main

if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1")
    port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
