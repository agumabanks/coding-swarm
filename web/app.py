"""
Sanaa Web Interface - VS Code-inspired IDE for AI Coding Assistance
Provides a comprehensive web-based interface with full CLI functionality
"""
from __future__ import annotations

import os
import json
import asyncio
import secrets
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from coding_swarm_core import (
    get_security_manager,
    get_enhanced_api,
    get_performance_monitor,
    get_advanced_orchestrator,
    get_advanced_debugger,
    get_memory_optimizer
)


class SanaaWebApp:
    """Main Sanaa Web Application"""

    def __init__(self):
        self.app = FastAPI(title="Sanaa Web IDE", version="2.0.0")
        self.templates = Jinja2Templates(directory="web/templates")
        self.static_path = Path("web/static")

        # Initialize core components
        self.security = get_security_manager()
        self.api = get_enhanced_api()
        self.monitor = get_performance_monitor()
        self.orchestrator = get_advanced_orchestrator()
        self.debugger = get_advanced_debugger()
        self.memory_optimizer = get_memory_optimizer()

        # WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

        self.setup_middleware()
        self.setup_routes()
        self.setup_websockets()

    def setup_middleware(self):
        """Setup FastAPI middleware"""

        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Session middleware
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=os.getenv("SANAA_SESSION_SECRET", secrets.token_hex(32))
        )

        # Custom middleware for request logging and monitoring
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = asyncio.get_event_loop().time()

            # Get client info
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            response = await call_next(request)

            # Calculate response time
            process_time = asyncio.get_event_loop().time() - start_time

            # Log request with host header for debugging
            host_header = request.headers.get("host", "unknown")
            print(f"[{datetime.utcnow()}] {request.method} {request.url.path} "
                  f"- Host: {host_header} - {response.status_code} - {process_time:.3f}s - {client_ip}")

            # Special logging for ai.sanaa.co domain
            if "ai.sanaa.co" in host_header:
                print(f"[DEBUG] Request to ai.sanaa.co: {request.method} {request.url} from {client_ip}")

            # Record metrics
            self.monitor.record_api_request(
                endpoint=request.url.path,
                duration=process_time,
                status_code=response.status_code,
                method=request.method
            )

            return response

    def setup_routes(self):
        """Setup web routes"""

        # Static files
        if self.static_path.exists():
            self.app.mount("/static", StaticFiles(directory=str(self.static_path)), name="static")

        # Authentication routes
        @self.app.get("/login")
        async def login_page(request: Request):
            return self.templates.TemplateResponse("login.html", {"request": request})

        @self.app.post("/api/auth/login")
        async def login(request: Request):
            data = await request.json()
            username = data.get("username")
            password = data.get("password")

            # Authenticate user (simplified for demo)
            if username and password:
                # Create session
                session_id = secrets.token_hex(16)
                self.user_sessions[session_id] = {
                    "user_id": username,
                    "username": username,
                    "login_time": datetime.utcnow()
                }

                response = JSONResponse({"success": True, "session_id": session_id})
                response.set_cookie("session_id", session_id, httponly=True)
                return response

            raise HTTPException(status_code=401, detail="Invalid credentials")

        @self.app.post("/api/auth/logout")
        async def logout(request: Request):
            session_id = request.cookies.get("session_id")
            if session_id and session_id in self.user_sessions:
                del self.user_sessions[session_id]

            response = JSONResponse({"success": True})
            response.delete_cookie("session_id")
            return response

        # Main application routes
        @self.app.get("/", response_class=HTMLResponse)
        async def home(request: Request):
            return self.templates.TemplateResponse("index.html", {"request": request})

        @self.app.get("/editor", response_class=HTMLResponse)
        async def editor(request: Request):
            return self.templates.TemplateResponse("editor.html", {"request": request})

        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard(request: Request):
            return self.templates.TemplateResponse("dashboard.html", {"request": request})

        @self.app.get("/projects", response_class=HTMLResponse)
        async def projects(request: Request):
            return self.templates.TemplateResponse("projects.html", {"request": request})

        @self.app.get("/agents", response_class=HTMLResponse)
        async def agents(request: Request):
            return self.templates.TemplateResponse("agents.html", {"request": request})

        @self.app.get("/monitoring", response_class=HTMLResponse)
        async def monitoring(request: Request):
            return self.templates.TemplateResponse("monitoring.html", {"request": request})

        @self.app.get("/docs", response_class=HTMLResponse)
        async def documentation(request: Request):
            return self.templates.TemplateResponse("docs.html", {"request": request})

        # API routes for functionality
        @self.app.get("/api/projects")
        async def get_projects():
            # Return mock projects data
            return {
                "projects": [
                    {
                        "id": "proj_1",
                        "name": "web-app",
                        "status": "active",
                        "last_modified": "2 hours ago",
                        "framework": "React",
                        "path": "/projects/web-app"
                    },
                    {
                        "id": "proj_2",
                        "name": "api-service",
                        "status": "building",
                        "last_modified": "30 minutes ago",
                        "framework": "FastAPI",
                        "path": "/projects/api-service"
                    }
                ]
            }

        @self.app.get("/api/agents")
        async def get_agents():
            # Return mock agents data
            return {
                "agents": [
                    {
                        "id": "agent_1",
                        "name": "Architect",
                        "status": "idle",
                        "type": "architect",
                        "capabilities": ["planning", "design", "architecture"],
                        "tasks_completed": 12,
                        "success_rate": 95.2
                    },
                    {
                        "id": "agent_2",
                        "name": "Coder",
                        "status": "active",
                        "type": "coder",
                        "capabilities": ["python", "javascript", "react", "node.js"],
                        "tasks_completed": 28,
                        "success_rate": 92.1
                    },
                    {
                        "id": "agent_3",
                        "name": "Debugger",
                        "status": "idle",
                        "type": "debugger",
                        "capabilities": ["debugging", "testing", "analysis"],
                        "tasks_completed": 8,
                        "success_rate": 98.5
                    }
                ]
            }

        @self.app.get("/api/system/status")
        async def get_system_status():
            # Get real system status
            health = await self.monitor.get_system_health()
            return {
                "status": "healthy" if health["overall_status"] == "healthy" else "degraded",
                "cpu_usage": health.get("cpu_usage", 0),
                "memory_usage": health.get("memory_usage", 0),
                "active_connections": len(self.active_connections),
                "uptime": "2 days, 4 hours",  # Mock uptime
                "version": "2.0.0"
            }

        @self.app.post("/api/command")
        async def execute_command(request: Request):
            """Execute CLI command via web interface"""
            data = await request.json()
            command = data.get("command", "")
            args = data.get("args", [])

            try:
                # Execute command (simplified - would integrate with actual CLI)
                result = await self._execute_cli_command(command, args)

                # Broadcast result to WebSocket clients
                await self.broadcast_command_result(command, result)

                return {"success": True, "result": result}

            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/api/files/{path:path}")
        async def get_file_content(path: str):
            """Get file content for editor"""
            try:
                file_path = Path(path)
                if file_path.exists() and file_path.is_file():
                    content = file_path.read_text()
                    return {
                        "path": str(file_path),
                        "content": content,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                else:
                    raise HTTPException(status_code=404, detail="File not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/api/files/{path:path}")
        async def save_file_content(path: str, request: Request):
            """Save file content from editor"""
            try:
                data = await request.json()
                content = data.get("content", "")

                file_path = Path(path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

                # Broadcast file change
                await self.broadcast_file_change(str(file_path), "modified")

                return {"success": True}

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    def setup_websockets(self):
        """Setup WebSocket endpoints"""

        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await websocket.accept()
            self.active_connections[client_id] = websocket

            try:
                while True:
                    data = await websocket.receive_json()

                    # Handle different message types
                    message_type = data.get("type")

                    if message_type == "command":
                        # Execute command
                        result = await self._execute_cli_command(
                            data.get("command", ""),
                            data.get("args", [])
                        )
                        await websocket.send_json({
                            "type": "command_result",
                            "command": data.get("command"),
                            "result": result
                        })

                    elif message_type == "file_watch":
                        # Start watching file for changes
                        file_path = data.get("path")
                        await self._watch_file_changes(websocket, file_path)

                    elif message_type == "subscribe":
                        # Subscribe to real-time updates
                        channel = data.get("channel")
                        # Implementation would handle subscriptions

            except WebSocketDisconnect:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]

    async def broadcast_command_result(self, command: str, result: Any):
        """Broadcast command result to all connected clients"""
        message = {
            "type": "command_result",
            "command": command,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

        for websocket in self.active_connections.values():
            try:
                await websocket.send_json(message)
            except:
                pass  # Client may have disconnected

    async def broadcast_file_change(self, file_path: str, change_type: str):
        """Broadcast file change to all connected clients"""
        message = {
            "type": "file_change",
            "path": file_path,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat()
        }

        for websocket in self.active_connections.values():
            try:
                await websocket.send_json(message)
            except:
                pass

    async def _execute_cli_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Execute CLI command (simplified implementation)"""
        # This would integrate with the actual CLI system
        if command == "status":
            return {"output": "System is running", "exit_code": 0}
        elif command == "projects":
            return {"output": "web-app, api-service", "exit_code": 0}
        elif command == "agents":
            return {"output": "Architect, Coder, Debugger", "exit_code": 0}
        else:
            return {"output": f"Command '{command}' executed", "exit_code": 0}

    async def _watch_file_changes(self, websocket: WebSocket, file_path: str):
        """Watch file for changes and send updates"""
        # Simplified file watching - in production, use watchdog or similar
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            last_modified = file_path_obj.stat().st_mtime

            while True:
                await asyncio.sleep(1)  # Check every second
                if file_path_obj.exists():
                    current_modified = file_path_obj.stat().st_mtime
                    if current_modified > last_modified:
                        content = file_path_obj.read_text()
                        await websocket.send_json({
                            "type": "file_update",
                            "path": file_path,
                            "content": content,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        last_modified = current_modified

    async def start_services(self):
        """Start all background services"""
        # Start monitoring
        await self.monitor.start_monitoring()

        # Start memory optimization
        self.memory_optimizer.start_optimization()

        # Start API services
        await self.api.initialize()

    async def stop_services(self):
        """Stop all background services"""
        await self.monitor.stop_monitoring()
        self.memory_optimizer.stop_optimization()

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance"""
        return self.app


# Global web app instance
sanaa_web_app = SanaaWebApp()


async def startup_event():
    """Application startup event"""
    await sanaa_web_app.start_services()


async def shutdown_event():
    """Application shutdown event"""
    await sanaa_web_app.stop_services()


# Create FastAPI app with lifecycle events
app = sanaa_web_app.get_app()

@app.on_event("startup")
async def startup():
    await startup_event()

@app.on_event("shutdown")
async def shutdown():
    await shutdown_event()


if __name__ == "__main__":
    port = int(os.getenv("SANAA_WEB_PORT", "8080"))
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )