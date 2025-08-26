# plugins/plugin_registry.py
import json
import importlib
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    capabilities: List[str]
    entry_point: str
    dependencies: List[str]
    config_schema: Dict[str, Any]

class PluginRegistry:
    """Advanced plugin system inspired by KiloCode's MCP marketplace."""
    
    def __init__(self):
        self.plugins: Dict[str, PluginMetadata] = {}
        self.loaded_plugins: Dict[str, Any] = {}
        self.registry_file = Path("plugins/registry.json")
    
    async def discover_plugins(self) -> List[PluginMetadata]:
        """Discover available plugins from registry."""
        if not self.registry_file.exists():
            await self._create_default_registry()
        
        registry_data = json.loads(self.registry_file.read_text())
        plugins = []
        
        for plugin_data in registry_data.get("plugins", []):
            plugin = PluginMetadata(**plugin_data)
            plugins.append(plugin)
            self.plugins[plugin.name] = plugin
        
        return plugins
    
    async def load_plugin(self, plugin_name: str) -> Any:
        """Dynamically load a plugin."""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]
        
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        plugin_meta = self.plugins[plugin_name]
        
        # Import plugin module
        module_name, class_name = plugin_meta.entry_point.split(":")
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name)
        
        # Initialize plugin
        plugin_instance = plugin_class()
        self.loaded_plugins[plugin_name] = plugin_instance
        
        return plugin_instance
    
    async def _create_default_registry(self):
        """Create default plugin registry."""
        default_registry = {
            "plugins": [
                {
                    "name": "code-quality-analyzer",
                    "version": "1.0.0",
                    "description": "Analyze code quality and suggest improvements",
                    "capabilities": ["static_analysis", "quality_metrics"],
                    "entry_point": "plugins.code_quality:CodeQualityPlugin",
                    "dependencies": ["pylint", "black", "mypy"],
                    "config_schema": {
                        "type": "object",
                        "properties": {
                            "max_line_length": {"type": "integer", "default": 88}
                        }
                    }
                },
                {
                    "name": "test-generator",
                    "version": "1.0.0", 
                    "description": "Generate unit tests for Python code",
                    "capabilities": ["test_generation", "coverage_analysis"],
                    "entry_point": "plugins.test_generator:TestGeneratorPlugin",
                    "dependencies": ["pytest"],
                    "config_schema": {
                        "type": "object",
                        "properties": {
                            "test_framework": {"type": "string", "default": "pytest"}
                        }
                    }
                }
            ]
        }
        
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(json.dumps(default_registry, indent=2))