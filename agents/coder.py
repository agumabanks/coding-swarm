from __future__ import annotations

from .base import Agent


class Coder(Agent):
    """Agent that applies code patches."""

    def apply_patch(self, patch: str) -> bool:
        # In a real implementation this method would apply ``patch`` to the
        # project.  The simplified version just stores the patch as an artifact
        # and reports success.
        self.artifacts["patch"] = patch
        return True
