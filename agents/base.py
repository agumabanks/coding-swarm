from __future__ import annotations

from typing import Any, Dict, Tuple


class Agent:
    """Base Agent interface shared by all specialized agents.

    Agents receive a shared ``context`` dictionary that can be
    used to exchange information and artifacts between steps.
    Each method returns simple primitives so the orchestrator can
    drive the workflow without caring about specific implementations.
    """

    def __init__(self, context: Dict[str, Any]) -> None:
        self.context = context
        # place for subclasses to store produced artifacts
        self.artifacts: Dict[str, Any] = {}

    # The following methods are intentionally no-op.  Sub-classes are
    # expected to override the ones that are relevant for their role.
    def plan(self) -> str:
        """Return a plan for the next action."""
        return ""

    def apply_patch(self, patch: str) -> bool:
        """Apply ``patch`` to the project.``patch`` semantics depend on the agent."""
        return False

    def run_tests(self) -> Tuple[bool, str]:
        """Run tests and return a tuple of (success, logs)."""
        return True, ""
