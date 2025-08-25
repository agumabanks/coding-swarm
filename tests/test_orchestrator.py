from __future__ import annotations

import pathlib, sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import agents.tester
from orchestrator.orchestrator import orchestrate


def test_orchestrator_flow(monkeypatch, tmp_path):
    def fake_run(cmd, capture_output, text):
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(agents.tester.subprocess, "run", fake_run)
    ctx = orchestrate("demo goal", project=str(tmp_path))
    assert ctx["success"] is True
    assert "plan" in ctx
