from __future__ import annotations

from typing import Any, Dict, Tuple

import typer

from coding_swarm_agents import create_agent

app = typer.Typer(add_completion=False)


def orchestrate(goal: str, project: str = ".") -> Dict[str, Any]:
    """Run the agents in sequence to accomplish ``goal``.

    A shared ``context`` dictionary is passed to every agent instance so they
    can exchange information and artifacts.  Each agent writes artifacts into
    its ``artifacts`` attribute which can be inspected by the orchestrator or
    later agents.
    """

    context: Dict[str, Any] = {"goal": goal, "project": project}

    architect = create_agent("architect", context)
    plan = architect.plan()
    context["plan"] = plan

    coder = create_agent("coder", context)
    coder.apply_patch(plan)

    tester = create_agent("tester", context)
    success, logs = tester.run_tests()
    context["logs"] = logs

    if not success:
        debugger = create_agent("debugger", context)
        debugger.apply_patch(logs)
        success, logs = tester.run_tests()
        context["logs"] = logs

    context["success"] = success
    return context


@app.command()
def run(goal: str, project: str = ".") -> None:
    """CLI entry point wrapping :func:`orchestrate`."""
    orchestrate(goal, project)


def main() -> None:
    app()
