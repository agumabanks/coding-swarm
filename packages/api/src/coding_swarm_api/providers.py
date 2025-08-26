from __future__ import annotations

import os
import json
from typing import List, Dict, Any, Optional

import httpx


class BaseProvider:
    """Abstract LLM provider."""

    def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    """Provider for OpenAI-compatible chat completions APIs.

    Defaults to using a locally hosted server such as ``llama.cpp``
    running on ``http://127.0.0.1:8080/v1``.  The endpoint and model can be
    overridden via ``OPENAI_BASE_URL``, ``OPENAI_API_KEY`` and
    ``OPENAI_MODEL`` environment variables.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "sk-local")
        self.model = model or os.getenv("OPENAI_MODEL", "llama-3.1")
        self.timeout = timeout

    def _endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        path = "/chat/completions" if base.endswith("/v1") else "/v1/chat/completions"
        return base + path

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self._endpoint(), json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data, indent=2)


PROVIDER_REGISTRY = {
    "openai-compatible": OpenAICompatibleProvider,
}


def get_provider(name: Optional[str] = None) -> BaseProvider:
    """Return provider instance by ``name`` (env ``CSWARM_PROVIDER``)."""
    name = name or os.getenv("CSWARM_PROVIDER", "openai-compatible")
    cls = PROVIDER_REGISTRY.get(name, OpenAICompatibleProvider)
    return cls()
