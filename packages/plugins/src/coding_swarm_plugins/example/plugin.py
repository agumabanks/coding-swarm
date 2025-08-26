"""Example plugin demonstrating the plugin API."""

from typing import Dict, Any


class ExampleAgent:
    """Very small agent used for demonstration."""

    def greet(self, name: str = "world") -> str:
        return f"hello {name}"


def greet(name: str = "world") -> str:
    """Simple command that greets the provided name."""
    return ExampleAgent().greet(name)


def register(registry: Dict[str, Dict[str, Any]]) -> None:
    """Register agent and command with the orchestrator registry."""
    registry["agents"]["example"] = ExampleAgent
    registry["commands"]["greet"] = greet
