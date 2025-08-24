#!/usr/bin/env bash
# cswarm-repair.sh — make this box healthy without reinstalling everything
# - fixes systemd ExecStart, pulls GGUF if missing, ensures clean compose up,
# - writes Nginx w/ websocket map, reloads, and runs smoke checks.

set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/coding-swarm/cswarm.env}"
INSTALL_DIR="${INSTALL_DIR:-/opt/coding-swarm}"
MODELS_DIR="${MODELS_DIR:-/opt/models}"
COMPOSE_FILE="${COMPOSE_FILE:-${INSTALL_DIR}/docker-compose.yml}"
SERVICE_API="${SERVICE_API:-swarm-api.service}"
SERVICE_AGENTS="${SERVICE_AGENTS:-coding-swarm-agents.service}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-9100}"
NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-45.94.58.252}"

mkdir -p "$INSTALL_DIR" "$MODELS_DIR"

# Load env if present
if [[ -f "$ENV_FILE" ]]; then
  set +u
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set -u
fi

# If API_PORT busy, pick an alternate and persist
if ss -ltn | awk '{print $4}' | grep -q ":${API_PORT}$"; then
  for p in 9100 9101 9102 9110; do
    if ! ss -ltn | awk '{print $4}' | grep -q ":${p}$"; then
      echo "ℹ API port ${API_PORT} busy; switching to ${p}"
      API_PORT="$p"
      break
    fi
  done
fi

# Persist API_PORT + NGINX_SERVER_NAME in env
if grep -q '^API_PORT=' "$ENV_FILE" 2>/dev/null; then
  sudo sed -i "s/^API_PORT=.*/API_PORT=\"${API_PORT}\"/" "$ENV_FILE"
else
  echo "API_PORT=\"${API_PORT}\"" | sudo tee -a "$ENV_FILE" >/dev/null
fi
if ! grep -q '^NGINX_SERVER_NAME=' "$ENV_FILE" 2>/dev/null; then
  echo "NGINX_SERVER_NAME=\"${NGINX_SERVER_NAME}\"" | sudo tee -a "$ENV_FILE" >/dev/null
fi

# --- Fix systemd ExecStart to absolute paths (no ${VAR} expansions) ---
if [[ -f /etc/systemd/system/"$SERVICE_API" ]]; then
  sudo sed -i 's#^ExecStart=.*#ExecStart=/opt/coding-swarm/venv/bin/python /opt/coding-swarm/bin/swarm_api.py#' /etc/systemd/system/"$SERVICE_API"
  sudo systemctl daemon-reload
fi

# --- Write a clean docker-compose.yml (no 6379 host port) ---
cat > "$COMPOSE_FILE" <<'YAML'
services:
  qwen-api:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0
      --port 8080
      --ctx-size 8192
      --parallel 2
      --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes:
      - /opt/models:/models:ro
    ports:
      - "8080:8080"

  qwen-web:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0
      --port 8081
      --ctx-size 8192
      --parallel 2
      --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes:
      - /opt/models:/models:ro
    ports:
      - "8081:8081"

  qwen-mobile:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0
      --port 8082
      --ctx-size 8192
      --parallel 2
      --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes:
      - /opt/models:/models:ro
    ports:
      - "8082:8082"

  qwen-test:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0
      --port 8083
      --ctx-size 8192
      --parallel 2
      --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes:
      - /opt/models:/models:ro
    ports:
      - "8083:8083"

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "no"]

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: swarm
      POSTGRES_PASSWORD: swarm
      POSTGRES_DB: swarm
    volumes:
      - coding_swarm_pgdata:/var/lib/postgresql/data

volumes:
  coding_swarm_pgdata:
YAML

# --- Ensure GGUF present ---
GGUF="${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
if [[ ! -f "$GGUF" ]]; then
  echo "==> Fetching model to ${GGUF} (one-time)"
  if ! command -v huggingface-cli >/dev/null 2>&1; then
    # permit root on Debian PEP 668 systems
    if command -v python3 >/dev/null 2>&1; then
      python3 -m pip -q install -U huggingface_hub --break-system-packages
    else
      apt-get update -qq && apt-get install -y -qq python3-pip && \
      python3 -m pip -q install -U huggingface_hub --break-system-packages
    fi
  fi
  huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
    --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
    --local-dir "$MODELS_DIR" \
    --local-dir-use-symlinks False
fi
ls -lh "$GGUF"

# --- Nginx with websocket upgrade map ---
sudo bash -c 'cat > /etc/nginx/conf.d/websocket.conf' <<'CONF'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ""      close;
}
CONF

SITE="/etc/nginx/sites-available/coding-swarm.conf"
sudo bash -c "cat > '$SITE'" <<EOF
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_pass http://${API_HOST}:${API_PORT};
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default || true
sudo ln -sf "$SITE" /etc/nginx/sites-enabled/coding-swarm.conf
sudo nginx -t && sudo systemctl reload nginx || true

# --- Restart compose + API ---
echo "==> Restarting agents (compose)"
(cd "$INSTALL_DIR" && docker compose down -v || true)
(cd "$INSTALL_DIR" && docker compose up -d)

echo "==> Restarting API service"
sudo systemctl restart "$SERVICE_API" || true

# --- Wait for llama servers to load model (health=200) ---
echo "==> Waiting for llama servers to become healthy..."
for p in 8080 8081 8082 8083; do
  for i in {1..60}; do
    if curl -fsS "http://127.0.0.1:${p}/health" >/dev/null 2>&1; then
      echo "  port ${p} ... OK"
      break
    fi
    sleep 2
    if (( i % 10 == 0 )); then
      echo "  port ${p} still loading (try ${i}/60)..."
    fi
  done
  # show last logs if still not ready
  if ! curl -fsS "http://127.0.0.1:${p}/health" >/dev/null 2>&1; then
    echo "  port ${p} did not become healthy; recent logs:"
    docker logs --tail=50 "coding-swarm-qwen-$(case $p in 8080) echo api ;; 8081) echo web ;; 8082) echo mobile ;; 8083) echo test ;; esac)-1" || true
  fi
done

# --- Quick API health (FastAPI) ---
echo -n "API /health on ${API_PORT} ... "
if curl -fsS "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
  echo "OK"
else
  echo "FAIL"
fi

echo "==> Public /info via Nginx"
curl -fsS "http://${NGINX_SERVER_NAME}/info" || true
echo
echo "Repair complete."
