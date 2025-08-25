from __future__ import annotations

from .base import Agent


class Debugger(Agent):
    """Agent that proposes a fix based on failing test logs."""

    def apply_patch(self, logs: str) -> bool:
        # Real debugger would produce a patch based on ``logs``.  We just store
        # the logs and mark success for demonstration purposes.
        self.artifacts["fix_patch"] = f"# fix based on logs\n{logs}"
        return True
