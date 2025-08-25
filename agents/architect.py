from __future__ import annotations

from .base import Agent


class Architect(Agent):
    """Agent responsible for producing a high level plan."""

    def plan(self) -> str:
        goal = self.context.get("goal", "")
        plan = f"Plan for goal: {goal}"
        self.artifacts["plan"] = plan
        return plan
