# Coding Swarm

- API: http://127.0.0.1:9101
- Public (via Nginx): http://45.94.58.252/info

Agents (llama.cpp) expected on:
- qwen-api     : 8080
- qwen-web     : 8081
- qwen-mobile  : 8082
- qwen-test    : 8083

Place a GGUF at: /opt/models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
Official llama.cpp server image: ghcr.io/ggerganov/llama.cpp:server  (HTTP API doc in repo). :contentReference[oaicite:6]{index=6}

## LLM Provider configuration

Coding‑Swarm now uses a pluggable provider layer.  By default it expects an
OpenAI‑compatible server running locally (for example `llama.cpp`) and will
connect to `http://127.0.0.1:8080/v1` using the model name from
`OPENAI_MODEL`.

Environment variables:

- `OPENAI_BASE_URL` – API base URL (default `http://127.0.0.1:8080/v1`)
- `OPENAI_API_KEY` – API token (default `sk-local`)
- `OPENAI_MODEL` – model identifier (default `llama-3.1`)
- `CSWARM_PROVIDER` – provider name (currently only `openai-compatible`)

The CLI entry point `bin/sanaa_orchestrator.py` also accepts `--provider` to
override the provider on a per‑run basis.
# coding-swarm
# coding-swarm
