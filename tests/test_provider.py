from __future__ import annotations

from types import SimpleNamespace
import pathlib, sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import api.providers as providers
from api.providers import OpenAICompatibleProvider, get_provider


def test_openai_provider_uses_base_url(monkeypatch):
    calls = {}

    class DummyResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "ok"}}]}

    class DummyClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def post(self, url, json, headers):  # type: ignore[override]
            calls["url"] = url
            calls["payload"] = json
            calls["headers"] = headers
            return DummyResp()

    monkeypatch.setattr(providers, "httpx", SimpleNamespace(Client=DummyClient))

    provider = OpenAICompatibleProvider()
    result = provider.chat([{"role": "user", "content": "hi"}])
    assert result == "ok"
    assert calls["url"].startswith("http://127.0.0.1:8080")
    assert calls["payload"]["model"] == provider.model


def test_get_provider_default():
    prov = get_provider()
    assert isinstance(prov, OpenAICompatibleProvider)
