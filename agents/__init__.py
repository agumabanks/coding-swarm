from __future__ import annotations

from importlib import import_module
from typing import Dict

from .base import Agent

# Registry mapping agent roles to "module:Class" strings.  New agent
# implementations can register themselves here without touching the
# orchestrator core logic.
AGENT_REGISTRY: Dict[str, str] = {
    "architect": "agents.architect:Architect",
    "coder": "agents.coder:Coder",
    "tester": "agents.tester:Tester",
    "debugger": "agents.debugger:Debugger",
}


def create_agent(role: str, context: Dict[str, object]) -> Agent:
    """Instantiate an agent for ``role`` using the registry."""
    path = AGENT_REGISTRY[role]
    module_name, class_name = path.split(":")
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls(context)
