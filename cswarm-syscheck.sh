#!/usr/bin/env bash
set -euo pipefail
API_PORT="${API_PORT:-9100}"
API_HOST="${API_HOST:-127.0.0.1}"
NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-45.94.58.252}"

echo "==> Coding Swarm System Check =="
echo "Host: $(hostname)  Time: $(date --iso-8601=seconds)"
ok=0; fail=0

chk() { # name cmd...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf "• %-30s OK\n" "$name"; ((ok++))
  else
    printf "• %-30s FAIL\n" "$name"; ((fail++))
  fi
}

# Basics
chk "docker present"         command -v docker
chk "docker compose present" docker compose version
chk "python3 present"        command -v python3
chk "curl present"           command -v curl
chk "jq present"             command -v jq

# Services/containers
chk "swarm-api service active" systemctl is-active --quiet swarm-api.service
chk "agents (compose) active"  bash -lc 'cd /opt/coding-swarm && docker compose ps --status=running | grep -q qwen-api'

for name in qwen-api qwen-web qwen-mobile qwen-test; do
  chk "container ${name} running" bash -lc "docker ps --format '{{.Names}}' | grep -q coding-swarm-${name}-1"
done

for p in 8080 8081 8082 8083; do
  chk "Llama server port ${p}" curl -fsS "http://127.0.0.1:${p}/health"
done

# FastAPI health
chk "API local /health (${API_PORT})" curl -fsS "http://${API_HOST}:${API_PORT}/health"

# Minimal chat completion against qwen-api llama server (should 200)
payload='{"model":"local","messages":[{"role":"user","content":"Say hi"}],"stream":false}'
chk "qwen-api responds /v1/chat/completions" bash -lc "curl -fsS -X POST http://127.0.0.1:8080/v1/chat/completions -H 'content-type: application/json' -d '$payload' | jq -e '.choices | length > 0'"

# Public via Nginx
chk "API public /info via Nginx (${NGINX_SERVER_NAME})" curl -fsS "http://${NGINX_SERVER_NAME}/info" 

echo
echo "Summary: PASS=${ok}  FAIL=${fail}  SKIP=0"
exit $(( fail > 0 ))
