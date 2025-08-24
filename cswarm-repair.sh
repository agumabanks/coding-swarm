#!/usr/bin/env bash
# Quick repair: stop conflicts, ensure model, fix Nginx map, restart compose/API
set -euo pipefail
ENV_FILE="/etc/coding-swarm/cswarm.env"
MODELS_DIR="/opt/models"
GGUF="${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
GGUF_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf?download=true"
INSTALL_DIR="/opt/coding-swarm"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
echo "==> Stopping any old coding-swarm compose/app"
(cd "$INSTALL_DIR" && docker compose down -v || true)
docker ps -aq --filter "name=qwen-" | xargs -r docker rm -f || true
docker ps -aq --filter "name=coding-swarm-" | xargs -r docker rm -f || true
mkdir -p "$MODELS_DIR"
if [[ ! -f "$GGUF" ]]; then
  if command -v hf &>/dev/null; then
    hf download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" --local-dir "$MODELS_DIR" --local-dir-use-symlinks False || true
  else
    curl -L --fail -o "$GGUF" "$GGUF_URL"
  fi
fi
ls -lh "$GGUF" || true
UPG="/etc/nginx/conf.d/upgrade-map.conf"
if [[ ! -f "$UPG" ]]; then
  cat > "$UPG" <<'CONF'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
CONF
fi
nginx -t && systemctl reload nginx || true
echo "==> Starting agents (docker compose) ..."
(cd "$INSTALL_DIR" && docker compose up -d)
echo "==> Restarting API"
systemctl restart swarm-api.service || true
echo "==> Smoke checks"
sleep 1
curl -fsS "http://127.0.0.1:${API_PORT}/health" || true
for p in 8080 8081 8082 8083; do echo -n "port $p: "; curl -fsS "http://127.0.0.1:${p}/health" >/dev/null && echo OK || echo FAIL; done
echo "Public /info via NGINX:"; curl -s "http://45.94.58.252/info" || true; echo
echo "Repair complete."
