# packages/core/src/coding_swarm_core/mcp_integration.py
"""MCP (Model Context Protocol) Integration for Coding Swarm"""

import json
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    command: List[str]
    args: List[str] = None
    env: Dict[str, str] = None
    description: str = ""
    capabilities: List[str] = None
    
    def __post_init__(self):
        self.args = self.args or []
        self.env = self.env or {}
        self.capabilities = self.capabilities or []

class MCPTransport(ABC):
    """Abstract MCP Transport"""
    
    @abstractmethod
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass

class STDIOTransport(MCPTransport):
    """STDIO Transport for local MCP servers"""
    
    def __init__(self, server: MCPServer):
        self.server = server
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process"""
        env = {**self.server.env, "PATH": os.environ.get("PATH", "")}
        
        self.process = subprocess.Popen(
            self.server.command + self.server.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        # Initialize the server
        await self._send_jsonrpc({
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "coding-swarm",
                    "version": "2.0.0"
                }
            }
        })
    
    async def stop(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params
        }
        
        return await self._send_jsonrpc(request)
    
    def _next_request_id(self) -> int:
        self.request_id += 1
        return self.request_id
    
    async def _send_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and get response"""
        if not self.process:
            raise RuntimeError("MCP server not started")
        
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        
        return json.loads(response_line.strip())

class MCPClient:
    """MCP Client for managing multiple servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.transports: Dict[str, MCPTransport] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
    
    async def add_server(self, server: MCPServer):
        """Add and start an MCP server"""
        transport = STDIOTransport(server)
        
        try:
            await transport.start()
            self.servers[server.name] = server
            self.transports[server.name] = transport
            
            # Discover tools and resources
            await self._discover_capabilities(server.name)
            
        except Exception as e:
            print(f"Failed to start MCP server {server.name}: {e}")
            await transport.stop()
    
    async def _discover_capabilities(self, server_name: str):
        """Discover tools and resources from a server"""
        transport = self.transports[server_name]
        
        # List available tools
        try:
            tools_response = await transport.send_request("tools/list", {})
            if "result" in tools_response and "tools" in tools_response["result"]:
                for tool in tools_response["result"]["tools"]:
                    tool_key = f"{server_name}:{tool['name']}"
                    self.tools[tool_key] = {
                        "server": server_name,
                        "tool": tool
                    }
        except Exception as e:
            print(f"Failed to list tools from {server_name}: {e}")
        
        # List available resources
        try:
            resources_response = await transport.send_request("resources/list", {})
            if "result" in resources_response and "resources" in resources_response["result"]:
                for resource in resources_response["result"]["resources"]:
                    resource_key = f"{server_name}:{resource['uri']}"
                    self.resources[resource_key] = {
                        "server": server_name,
                        "resource": resource
                    }
        except Exception as e:
            print(f"Failed to list resources from {server_name}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via MCP"""
        if tool_name not in self.tools:
            available_tools = list(self.tools.keys())
            raise ValueError(f"Tool {tool_name} not found. Available: {available_tools}")
        
        tool_info = self.tools[tool_name]
        server_name = tool_info["server"]
        transport = self.transports[server_name]
        
        return await transport.send_request("tools/call", {
            "name": tool_info["tool"]["name"],
            "arguments": arguments
        })
    
    async def read_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Read a resource via MCP"""
        resource_key = None
        for key in self.resources:
            if key.endswith(resource_uri):
                resource_key = key
                break
        
        if not resource_key:
            available_resources = list(self.resources.keys())
            raise ValueError(f"Resource {resource_uri} not found. Available: {available_resources}")
        
        resource_info = self.resources[resource_key]
        server_name = resource_info["server"]
        transport = self.transports[server_name]
        
        return await transport.send_request("resources/read", {
            "uri": resource_info["resource"]["uri"]
        })
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [
            {
                "name": tool_name,
                "server": tool_info["server"],
                "description": tool_info["tool"].get("description", ""),
                "schema": tool_info["tool"].get("inputSchema", {})
            }
            for tool_name, tool_info in self.tools.items()
        ]
    
    def list_available_resources(self) -> List[Dict[str, Any]]:
        """List all available resources"""
        return [
            {
                "uri": resource_info["resource"]["uri"],
                "server": resource_info["server"],
                "description": resource_info["resource"].get("description", ""),
                "mimeType": resource_info["resource"].get("mimeType", "")
            }
            for resource_key, resource_info in self.resources.items()
        ]
    
    async def shutdown(self):
        """Shutdown all MCP servers"""
        for transport in self.transports.values():
            await transport.stop()
        
        self.servers.clear()
        self.transports.clear()
        self.tools.clear()
        self.resources.clear()

# MCP Server Registry - Built-in servers similar to KiloCode's marketplace
BUILTIN_SERVERS = {
    "filesystem": MCPServer(
        name="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
        args=["/path/to/allowed/directory"],
        description="File system operations",
        capabilities=["read_file", "write_file", "create_directory", "list_directory"]
    ),
    "git": MCPServer(
        name="git",
        command=["npx", "-y", "@modelcontextprotocol/server-git"],
        description="Git repository operations",
        capabilities=["git_log", "git_diff", "git_status", "git_show"]
    ),
    "github": MCPServer(
        name="github",
        command=["npx", "-y", "@modelcontextprotocol/server-github"],
        description="GitHub API integration",
        capabilities=["create_issue", "list_repos", "search_repos"]
    ),
    "brave-search": MCPServer(
        name="brave-search",
        command=["npx", "-y", "@modelcontextprotocol/server-brave-search"],
        description="Web search via Brave",
        capabilities=["web_search"]
    )
}

class MCPRegistry:
    """Registry for MCP servers similar to KiloCode's marketplace"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".coding-swarm" / "mcp-servers.json"
        self.custom_servers: Dict[str, MCPServer] = {}
        self.load_custom_servers()
    
    def load_custom_servers(self):
        """Load custom MCP servers from config"""
        if not self.config_path.exists():
            return
        
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            
            for name, server_config in config.items():
                self.custom_servers[name] = MCPServer(**server_config)
        except Exception as e:
            print(f"Failed to load MCP server config: {e}")
    
    def save_custom_servers(self):
        """Save custom MCP servers to config"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            name: {
                "name": server.name,
                "command": server.command,
                "args": server.args,
                "env": server.env,
                "description": server.description,
                "capabilities": server.capabilities
            }
            for name, server in self.custom_servers.items()
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def add_custom_server(self, server: MCPServer):
        """Add a custom MCP server"""
        self.custom_servers[server.name] = server
        self.save_custom_servers()
    
    def get_all_servers(self) -> Dict[str, MCPServer]:
        """Get all available servers (builtin + custom)"""
        return {**BUILTIN_SERVERS, **self.custom_servers}
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a specific server by name"""
        all_servers = self.get_all_servers()
        return all_servers.get(name)

# Integration with existing agent system
class MCPEnhancedAgent:
    """Agent enhanced with MCP capabilities"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.registry = MCPRegistry()
    
    async def initialize_mcp(self, server_names: List[str]):
        """Initialize MCP with specified servers"""
        for server_name in server_names:
            server = self.registry.get_server(server_name)
            if server:
                await self.mcp_client.add_server(server)
            else:
                print(f"Unknown MCP server: {server_name}")
    
    async def execute_with_mcp(self, task: str, context: Dict[str, Any]):
        """Execute a task with MCP tool assistance"""
        # Determine which tools might be helpful
        available_tools = self.mcp_client.list_available_tools()
        
        # This would integrate with your existing LLM calls
        # The LLM would see available tools and choose which to use
        system_prompt = f"""
You have access to the following MCP tools:
{json.dumps(available_tools, indent=2)}

Use these tools to help complete the task: {task}
Call tools using the format: mcp_call(tool_name, arguments)
"""
        
        # Your existing agent execution logic here
        # Enhanced with MCP tool calling capabilities
        
    async def cleanup(self):
        """Cleanup MCP resources"""
        await self.mcp_client.shutdown()