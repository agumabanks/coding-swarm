# api/streaming.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
import asyncio

class StreamingOrchestrator:
    """Real-time streaming similar to KiloCode's VS Code integration."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_streams: Dict[str, asyncio.Queue] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect new client for streaming."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.task_streams[client_id] = asyncio.Queue()
    
    async def disconnect(self, client_id: str):
        """Disconnect client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.task_streams:
            del self.task_streams[client_id]
    
    async def stream_task_execution(self, client_id: str, goal: str, project: str):
        """Stream task execution progress to client."""
        websocket = self.active_connections[client_id]
        
        try:
            # Initialize orchestration
            await self._send_update(websocket, "init", {"goal": goal, "project": project})
            
            # Execute with streaming updates
            from orchestrator.advanced_orchestrator import AdvancedOrchestrator
            orchestrator = AdvancedOrchestrator()
            
            # Hook into orchestrator events for streaming
            results = await orchestrator.orchestrate_with_streaming(
                goal, project, self._create_stream_callback(websocket)
            )
            
            await self._send_update(websocket, "complete", results)
            
        except Exception as e:
            await self._send_update(websocket, "error", {"error": str(e)})
    
    def _create_stream_callback(self, websocket: WebSocket):
        """Create callback for streaming orchestrator events."""
        async def callback(event_type: str, data: Any):
            await self._send_update(websocket, event_type, data)
        return callback
    
    async def _send_update(self, websocket: WebSocket, event_type: str, data: Any):
        """Send update to client via WebSocket."""
        message = {
            "type": event_type,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        await websocket.send_text(json.dumps(message))

# FastAPI integration
app = FastAPI()
streaming_orchestrator = StreamingOrchestrator()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await streaming_orchestrator.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "execute_task":
                await streaming_orchestrator.stream_task_execution(
                    client_id, message["goal"], message["project"]
                )
    except WebSocketDisconnect:
        await streaming_orchestrator.disconnect(client_id)