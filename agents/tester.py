from __future__ import annotations

import subprocess
from .base import Agent


class Tester(Agent):
    """Agent that runs the project's test suite."""

    def run_tests(self) -> tuple[bool, str]:
        result = subprocess.run(["pytest"], capture_output=True, text=True)
        logs = result.stdout + result.stderr
        self.artifacts["logs"] = logs
        return result.returncode == 0, logs
