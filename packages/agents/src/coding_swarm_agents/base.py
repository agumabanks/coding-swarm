from __future__ import annotations

from typing import Any, Dict, Tuple, Optional
import os
import httpx
from pathlib import Path


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
        # LLM provider integration
        self._llm_client: Optional[httpx.AsyncClient] = None
        self.model_base = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
        self.model_name = os.getenv("OPENAI_MODEL", "qwen2.5-coder-7b-instruct-q4_k_m")
        self.api_key = os.getenv("OPENAI_API_KEY", "sk-local")

    async def _call_llm(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Call the local LLM with proper error handling"""
        try:
            if not self._llm_client:
                self._llm_client = httpx.AsyncClient(
                    base_url=self.model_base,
                    timeout=60.0
                )

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = await self._llm_client.post(
                "/chat/completions",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"LLM Error: {response.status_code} - {response.text}"

        except Exception as e:
            return f"LLM Connection Error: {str(e)}"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent type"""
        return "You are an expert coding assistant."

    def _get_project_context(self) -> str:
        """Get project context information"""
        project_path = self.context.get('project', '.')
        context_info = f"Project: {project_path}\n"

        # Try to detect framework
        project_dir = Path(project_path)
        if (project_dir / 'package.json').exists():
            context_info += "Framework: React/Node.js\n"
        elif (project_dir / 'artisan').exists():
            context_info += "Framework: Laravel/PHP\n"
        elif (project_dir / 'pubspec.yaml').exists():
            context_info += "Framework: Flutter/Dart\n"

        return context_info

    async def _generate_response(self, user_query: str, context: str = "") -> str:
        """Generate an intelligent response using the LLM"""
        system_prompt = self._get_system_prompt()
        project_context = self._get_project_context()

        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\nProject Context:\n{project_context}\n{context}"
            },
            {
                "role": "user",
                "content": user_query
            }
        ]

        return await self._call_llm(messages)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._llm_client:
            await self._llm_client.aclose()

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
