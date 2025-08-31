from __future__ import annotations

from importlib import import_module
from typing import Dict

from .base import Agent

# Registry mapping agent roles to "module:Class" strings.  New agent
# implementations can register themselves here without touching the
# orchestrator core logic.
AGENT_REGISTRY: Dict[str, str] = {
    "architect": "coding_swarm_agents.architect:Architect",
    "coder": "coding_swarm_agents.coder:Coder",
    "tester": "coding_swarm_agents.tester:Tester",
    "debugger": "coding_swarm_agents.debugger:Debugger",
    # Specialized framework agents
    "react": "coding_swarm_agents.react_agent:ReactAgent",
    "laravel": "coding_swarm_agents.laravel_agent:LaravelAgent",
    "flutter": "coding_swarm_agents.flutter_agent:FlutterAgent",
    # Advanced debugging
    "advanced_debugger": "coding_swarm_agents.advanced_debugger:AdvancedDebuggerAgent",
    # Planning and strategy
    "planner": "coding_swarm_agents.planning_agent:PlanningAgent",
}


def create_agent(role: str, context: Dict[str, object]) -> Agent:
    """Instantiate an agent for ``role`` using the registry."""
    path = AGENT_REGISTRY[role]
    module_name, class_name = path.split(":")
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls(context)
