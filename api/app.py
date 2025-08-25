"""Task orchestration API using FastAPI."""
from __future__ import annotations

import asyncio
import os
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from pydantic import BaseModel

try:  # optional redis backend
    import redis.asyncio as redis
except Exception:  # pragma: no cover - redis is optional
    redis = None

app = FastAPI()


class TaskStore:
    """Abstract task metadata store."""

    async def create(self, task_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def set_status(self, task_id: str, status: str) -> None:
        raise NotImplementedError

    async def append_log(self, task_id: str, line: str) -> None:
        raise NotImplementedError

    async def get_status(self, task_id: str) -> Optional[str]:
        raise NotImplementedError

    async def get_logs(self, task_id: str) -> Optional[List[str]]:
        raise NotImplementedError


class MemoryStore(TaskStore):
    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, List[str] | str]] = {}

    async def create(self, task_id: str) -> None:
        self.tasks[task_id] = {"status": "pending", "logs": []}

    async def set_status(self, task_id: str, status: str) -> None:
        self.tasks.setdefault(task_id, {"logs": []})["status"] = status

    async def append_log(self, task_id: str, line: str) -> None:
        self.tasks.setdefault(task_id, {"status": "running", "logs": []})["logs"].append(line)

    async def get_status(self, task_id: str) -> Optional[str]:
        task = self.tasks.get(task_id)
        return task["status"] if task else None

    async def get_logs(self, task_id: str) -> Optional[List[str]]:
        task = self.tasks.get(task_id)
        return list(task["logs"]) if task else None


class RedisStore(TaskStore):
    def __init__(self, client: "redis.Redis") -> None:
        self.client = client

    def _key(self, task_id: str) -> str:
        return f"task:{task_id}"

    def _log_key(self, task_id: str) -> str:
        return f"task:{task_id}:logs"

    async def create(self, task_id: str) -> None:
        await self.client.hset(self._key(task_id), mapping={"status": "pending"})
        await self.client.delete(self._log_key(task_id))

    async def set_status(self, task_id: str, status: str) -> None:
        await self.client.hset(self._key(task_id), "status", status)

    async def append_log(self, task_id: str, line: str) -> None:
        await self.client.rpush(self._log_key(task_id), line)

    async def get_status(self, task_id: str) -> Optional[str]:
        return await self.client.hget(self._key(task_id), "status")

    async def get_logs(self, task_id: str) -> Optional[List[str]]:
        exists = await self.client.exists(self._key(task_id))
        if not exists:
            return None
        logs = await self.client.lrange(self._log_key(task_id), 0, -1)
        return [l.decode() if isinstance(l, bytes) else l for l in logs]


async def _get_store() -> TaskStore:
    url = os.getenv("REDIS_URL")
    if url and redis is not None:
        client = redis.from_url(url)
        return RedisStore(client)
    return MemoryStore()


store: TaskStore
listeners: Dict[str, List[asyncio.Queue]] = {}


@app.on_event("startup")
async def on_startup() -> None:
    global store
    store = await _get_store()


class StartRequest(BaseModel):
    command: str = "echo 'hello from task'"


async def run_task(task_id: str, command: str) -> None:
    await store.set_status(task_id, "running")
    await broadcast(task_id, {"event": "status", "data": "running"})
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    assert proc.stdout
    async for line in proc.stdout:
        text = line.decode().rstrip()
        await store.append_log(task_id, text)
        await broadcast(task_id, {"event": "log", "data": text})
    code = await proc.wait()
    status = "finished" if code == 0 else "error"
    await store.set_status(task_id, status)
    await broadcast(task_id, {"event": "status", "data": status})


async def broadcast(task_id: str, message: dict) -> None:
    qs = listeners.get(task_id, [])
    for q in qs:
        await q.put(message)


@app.post("/tasks/start")
async def start_task(req: StartRequest, background: BackgroundTasks) -> dict:
    task_id = str(uuid4())
    await store.create(task_id)
    background.add_task(run_task, task_id, req.command)
    return {"id": task_id}


@app.get("/tasks/{task_id}/status")
async def task_status(task_id: str) -> dict:
    status = await store.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": status}


@app.get("/tasks/{task_id}/logs")
async def task_logs(task_id: str) -> dict:
    logs = await store.get_logs(task_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "logs": logs}


@app.websocket("/ws/tasks/{task_id}")
async def task_ws(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    queue = asyncio.Queue()
    listeners.setdefault(task_id, []).append(queue)
    try:
        status = await store.get_status(task_id)
        if status:
            await websocket.send_json({"event": "status", "data": status})
        logs = await store.get_logs(task_id)
        if logs:
            for line in logs:
                await websocket.send_json({"event": "log", "data": line})
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        listeners[task_id].remove(queue)
        if not listeners[task_id]:
            listeners.pop(task_id, None)
