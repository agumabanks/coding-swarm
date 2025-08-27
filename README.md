# Sanaa — Coding Swarm CLI

Sanaa is an all-in-one, open-source AI coding assistant that runs locally against your models.
It combines multiple “modes”:

- **Architect** – designs solutions before you write code
- **Code** – turns plans into production-ready code
- **Debug** – finds and fixes issues
- **Orchestrator** – breaks complex goals into delegated subtasks

Sanaa aims to be batteries-included and easy to use (inspired by Kilo Code’s “brings together the best features of AI coding tools, and still easy to use” ethos). :contentReference[oaicite:2]{index=2}

---

## Prerequisites

- **Python 3.11+** with `venv`
- **Local model server (OpenAI-compatible)**  
  This repo defaults to your running `llama.cpp` servers. The `llama-cpp-python`/`llama.cpp` web server exposes an OpenAI-compatible `/v1` API you can call with standard Chat Completions. :contentReference[oaicite:3]{index=3}

Your current containers (from `docker ps`) look like:

- `coding-swarm-qwen-api-1` on **:8080** (healthy) – default base
- `coding-swarm-qwen-web-1` on :8081
- `coding-swarm-qwen-mobile-1` on :8082
- `coding-swarm-qwen-test-1` on :8083
- `redis:7-alpine` and `postgres:16-alpine` (optional for advanced features)

---

## Quick start

```bash
# 1) create/refresh venv, install editable packages
python3 tools/bootstrap.py
source .venv/bin/activate

# 2) run the CLI (interactive)
sanaa
# or, if PATH doesn't have it:
.venv/bin/swarm-orchestrator


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
