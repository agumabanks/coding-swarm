#!/usr/bin/env bash
# cswarm-all.sh
# One-file installer + syscheck + repair for "Coding Swarm" on Debian/Ubuntu
# - Installs OS deps, Python venv, FastAPI service, Nginx (optional)
# - Brings up dockerized llama.cpp lanes + redis + postgres (no host port conflicts)
# - Downloads Qwen2.5 Coder 7B Instruct GGUF with 'hf download' into /opt/models
# - Provides syscheck + repair subcommands
#
# Usage:
#   sudo $0 install [--full] [--with-nginx] [--nginx-server-name HOST] [--model-path /opt/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf]
#   sudo $0 syscheck
#   sudo $0 repair
#
# Example:
#   sudo $0 install --full --with-nginx --nginx-server-name 45.94.58.252
#
# Notes:
# - Requires root/sudo
# - Safe to re-run; idempotent where possible
# - Script writes to: /opt/coding-swarm (code, compose), /etc/coding-swarm (env), /opt/models (GGUF)
# - API serves on 127.0.0.1:$API_PORT and (optionally) Nginx proxies http://<server>/ to it
#
set -euo pipefail

# ------------------------------ Defaults --------------------------------
SYSTEM_TYPE="debian"
SITE_NAME="coding-swarm"
SWARM_USER="swarm"

INSTALL_DIR="/opt/coding-swarm"
BIN_DIR="${INSTALL_DIR}/bin"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="/var/log/coding-swarm"
ETC_DIR="/etc/coding-swarm"
ENV_FILE="${ETC_DIR}/cswarm.env"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
MODELS_DIR="/opt/models"

API_HOST_DEFAULT="127.0.0.1"
API_PORTS_CANDIDATE=(9100 9101 9102 9110)

NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-}"
WITH_NGINX="false"
FULL_INSTALL="false"
MODEL_PATH=""
OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://45.94.58.252}"
BACKUP_MODELS="${BACKUP_MODELS:-gpt-4o,claude-3-sonnet}"

TOTAL_STEPS=20
STEP=0

# ------------------------------ UI utils --------------------------------
bar() {  # bar current total
  local cur="$1" total="$2" width=40
  local filled=$(( cur * width / total ))
  local empty=$(( width - filled ))
  printf "\r["
  printf "%0.s█" $(seq 1 $filled)
  printf "%0.s░" $(seq 1 $empty)
  printf "] "
}
say()   { echo -e "$*"; }
ok()    { echo -e "DONE"; }
warn()  { echo -e "\033[33mWARN:\033[0m $*"; }
fail()  { echo -e "\033[31mERROR:\033[0m $*"; }
info()  { echo -e "\033[36m$*\033[0m"; }
step()  { STEP=$((STEP+1)); bar "$STEP" "$TOTAL_STEPS"; echo -n " ($STEP/$TOTAL_STEPS) $1"; echo; }

# ------------------------------ Parse args ------------------------------
cmd="${1:-}"
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-nginx)            WITH_NGINX="true"; shift;;
    --full)                  FULL_INSTALL="true"; shift;;
    --nginx-server-name)     NGINX_SERVER_NAME="$2"; shift 2;;
    --model-path)            MODEL_PATH="$2"; shift 2;;
    --help|-h)
      cat <<USAGE
Usage:
  sudo $0 install [--full] [--with-nginx] [--nginx-server-name HOST] [--model-path /opt/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf]
  sudo $0 syscheck
  sudo $0 repair

Examples:
  sudo $0 install --full --with-nginx --nginx-server-name 45.94.58.252
USAGE
      exit 0;;
    *) break;;
  esac
done

if [[ -z "${cmd}" ]]; then
  fail "No subcommand. Use: install | syscheck | repair"
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  fail "Run as root (sudo)."
  exit 2
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$LOG_DIR" "$ETC_DIR" "$MODELS_DIR"

# ------------------------------ Helpers ---------------------------------
choose_free_port() {
  for p in "${API_PORTS_CANDIDATE[@]}"; do
    if ! ss -ltn | awk '{print $4}' | grep -q ":${p}$"; then
      echo "$p"; return 0
    fi
  done
  echo "9100"
}

persist_env_kv() {
  local key="$1" val="$2"
  grep -q "^${key}=" "$ENV_FILE" 2>/dev/null \
    && sed -i "s|^${key}=.*|${key}=\"${val}\"|g" "$ENV_FILE" \
    || echo "${key}=\"${val}\"" >> "$ENV_FILE"
}

have() { command -v "$1" >/dev/null 2>&1; }

apt_install() {
  DEBIAN_FRONTEND=noninteractive apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@" \
    || { warn "apt reported problems; attempting repair"; \
         DEBIAN_FRONTEND=noninteractive apt-get -f -y install; \
         DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@" || return 1; }
}

sysd_reload_enable_restart() {
  systemctl daemon-reload || true
  systemctl enable "$1" 2>/dev/null || true
  systemctl restart "$1" || true
}

compose_down() { (cd "$INSTALL_DIR" && docker compose down -v || true); }
compose_up()   { (cd "$INSTALL_DIR" && docker compose up -d); }

# ------------------------------ Files -----------------------------------
write_compose() {
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

  # internal only (no host port exposure, avoids 6379 conflicts)
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
}

write_api_py() {
  mkdir -p "$BIN_DIR"
cat > "${BIN_DIR}/swarm_api.py" <<'PY'
#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

ENV_FILE="/etc/coding-swarm/cswarm.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.strip().split('=',1)
                os.environ[k]=v.strip('"')

app = FastAPI(title="Coding Swarm API", version="2.0.0")

class RunRequest(BaseModel):
    goal: str
    project: str = "."
    model: Optional[str] = None
    dry_run: bool = False

@app.get("/health")
async def health():
    return {"status":"ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/info")
async def info():
    return {
        "service":"Coding Swarm API",
        "version":"2.0.0",
        "host": os.getenv("API_HOST","127.0.0.1"),
        "port": int(os.getenv("API_PORT","9100")),
    }

@app.post("/run")
async def run(req: RunRequest):
    proj = Path(req.project).resolve()
    if not proj.exists():
        raise HTTPException(400, "Project directory does not exist")
    return {"received": req.dict(), "ts": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1")
    port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
PY
chmod +x "${BIN_DIR}/swarm_api.py"
}

write_api_service() {
cat > /etc/systemd/system/swarm-api.service <<SERVICE
[Unit]
Description=Coding Swarm API
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
Group=root
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/python ${BIN_DIR}/swarm_api.py
WorkingDirectory=${BIN_DIR}
Restart=on-failure
RestartSec=3

# hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICE
}

write_nginx_map() {
# map must live in http{} context -> conf.d file
cat > /etc/nginx/conf.d/coding-swarm-upgrade-map.conf <<'NGX'
# WebSocket upgrade helper
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
NGX
}

write_nginx_site() {
local srv="$1" api_port="$2"
cat > /etc/nginx/sites-available/${SITE_NAME}.conf <<NGINX
server {
    listen 80;
    server_name ${srv};

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_pass http://127.0.0.1:${api_port};
    }
}
NGINX

ln -sf /etc/nginx/sites-available/${SITE_NAME}.conf /etc/nginx/sites-enabled/${SITE_NAME}.conf
# remove default + any duplicates for same server_name
rm -f /etc/nginx/sites-enabled/default || true
for f in /etc/nginx/sites-enabled/*; do
  [[ -f "$f" ]] || continue
  if grep -q "server_name ${srv}" "$f" && [[ "$f" != "/etc/nginx/sites-enabled/${SITE_NAME}.conf" ]]; then
    rm -f "$f"
  fi
done
nginx -t
systemctl reload nginx
}

download_model_if_needed() {
  local target="${1}"
  if [[ -z "$target" ]]; then
    target="${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
  fi
  if [[ -f "$target" ]]; then
    ls -lh "$target"
    return 0
  fi

  info "Downloading GGUF with 'hf download' (Qwen2.5 7B Instruct Q4_K_M) -> ${target}"
  "${VENV_DIR}/bin/pip" -q install -U "huggingface_hub[cli]" || true
  # newer CLI is 'hf', older is 'huggingface-cli' – prefer 'hf'
  if [[ -x "${VENV_DIR}/bin/hf" ]]; then
    "${VENV_DIR}/bin/hf" download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
      --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
      --local-dir "${MODELS_DIR}" \
      --local-dir-use-symlinks False
  else
    "${VENV_DIR}/bin/huggingface-cli" download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
      --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" \
      --local-dir "${MODELS_DIR}" \
      --local-dir-use-symlinks False
  fi
  ls -lh "${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
}

syscheck_block() {
  local host="${1}" port="${2}" public="${3:-}"
  echo "==> Coding Swarm System Check =="
  echo "Host: $(hostname)  Time: $(date -Iseconds)"
  local pass=0 failc=0

  for tool in docker curl jq python3; do
    if have "$tool"; then echo "• ${tool} present ... OK"; ((pass++)); else echo "• ${tool} present ... FAIL"; ((failc++)); fi
  done

  if systemctl is-active --quiet swarm-api.service; then
    echo "• swarm-api service active ... OK"; ((pass++))
  else
    echo "• swarm-api service active ... FAIL"; ((failc++))
  fi

  # containers
  local names=(qwen-api qwen-web qwen-mobile qwen-test redis postgres)
  local okc=0
  for n in "${names[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "${SITE_NAME}-${n}-1\|${n}$\|${SITE_NAME}_${n}_1"; then
      echo "• container ${n} running ... OK"; ((okc++))
    else
      echo "• container ${n} running ... FAIL"; ((failc++))
    fi
  done

  # health of llama servers
  for p in 8080 8081 8082 8083; do
    if curl -fsS "http://127.0.0.1:${p}/health" >/dev/null 2>&1; then
      echo "• Llama server port ${p} ... OK"; ((pass++))
    else
      echo "• Llama server port ${p} ... FAIL"; ((failc++))
    fi
  done

  # API health
  if curl -fsS "http://${host}:${port}/health" >/dev/null 2>&1; then
    echo "• API local /health (${port}) ... OK"; ((pass++))
  else
    echo "• API local /health (${port}) ... FAIL"; ((failc++))
  fi

  # public check via nginx
  if [[ -n "$public" ]]; then
    if curl -fsS "http://${public}/info" | jq -r '.service' >/dev/null 2>&1; then
      echo "• API public /info via Nginx (${public}) ... OK"; ((pass++))
    else
      echo "• API public /info via Nginx (${public}) ... FAIL"; ((failc++))
    fi
  fi

  # GGUF present?
  if ls -1 "${MODELS_DIR}"/qwen2.5-coder-7b-instruct-q4_k_m.gguf >/dev/null 2>&1; then
    echo "• GGUF model present ... OK"; ((pass++))
  else
    echo "• GGUF model present ... FAIL"; ((failc++))
  fi

  echo
  echo "Summary: PASS=${pass}  FAIL=${failc}"
  [[ "$failc" -eq 0 ]]
}

# ------------------------------ INSTALL ---------------------------------
install_cmd() {
  echo
  info "Detected system: ${SYSTEM_TYPE}"
  info "Host resources: RAM=$(awk '/MemTotal/ {printf \"%dMB\", $2/1024}' /proc/meminfo), CPU=$(nproc), free disk ~$(df -h / | awk 'NR==2 {print $4}')"
  local api_port="$(choose_free_port)"
  [[ -z "${NGINX_SERVER_NAME}" ]] && NGINX_SERVER_NAME="$(hostname -I | awk '{print $1}')"

  step "Create user & directories"
  id -u "$SWARM_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$SWARM_USER" || true
  usermod -aG docker "$SWARM_USER" 2>/dev/null || true
  mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$VENV_DIR" "$LOG_DIR" "$ETC_DIR" "$MODELS_DIR"
  touch "$ENV_FILE"
  ok

  step "Install/verify OS deps (Docker, compose, Python, curl, jq)"
  apt_install ca-certificates curl jq git unzip htop lsb-release \
      python3 python3-venv python3-pip \
      docker.io docker-compose-plugin nginx || true
  ok

  step "Write env"
  cat > "$ENV_FILE" <<EOF
API_HOST="${API_HOST_DEFAULT}"
API_PORT="${api_port}"
OPENAI_MODEL="${OPENAI_MODEL}"
OPENAI_BASE_URL="${OPENAI_BASE_URL}"
BACKUP_MODELS="${BACKUP_MODELS}"
VENV_DIR="${VENV_DIR}"
BIN_DIR="${BIN_DIR}"
EOF
  chmod 640 "$ENV_FILE"
  ok

  step "Python venv & deps (FastAPI, Uvicorn, huggingface-hub CLI)"
  python3 -m venv "$VENV_DIR" 2>/dev/null || true
  "${VENV_DIR}/bin/pip" -q install --upgrade pip wheel setuptools
  "${VENV_DIR}/bin/pip" -q install "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2" "huggingface_hub[cli]>=0.22"
  ok

  step "Write API server & systemd unit"
  write_api_py
  write_api_service
  sysd_reload_enable_restart "swarm-api.service"
  ok

  step "Write docker-compose.yml"
  write_compose
  ok

  step "Download GGUF (if missing)"
  if [[ -n "$MODEL_PATH" ]]; then
    if [[ -f "$MODEL_PATH" ]]; then
      cp -n "$MODEL_PATH" "${MODELS_DIR}/" || true
    else
      warn "--model-path given but file not found: $MODEL_PATH"
    fi
  fi
  download_model_if_needed "${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf" || warn "Model download skipped/failed"
  ok

  step "Compose up (agents)"
  compose_down
  compose_up
  ok

  if [[ "$WITH_NGINX" == "true" ]]; then
    step "Nginx configuration"
    write_nginx_map
    write_nginx_site "$NGINX_SERVER_NAME" "$api_port"
    ok
  else
    step "Nginx configuration"
    warn "Nginx disabled (use --with-nginx to enable)"; ok
  fi

  step "Logrotate & finish touches"
  cat > /etc/logrotate.d/coding-swarm <<'LR'
/var/log/coding-swarm/*.log {
    rotate 7
    daily
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
LR
  ok

  echo
  echo "=================================================="
  echo "Summary"
  echo "=================================================="
  echo " ✅ DONE:"
  echo "  - User & dirs ready"
  echo "  - Deps & Docker/Compose"
  echo "  - Config written to ${ENV_FILE}"
  echo "  - Python deps installed"
  echo "  - Orchestrator API written & systemd active"
  echo "  - Agents defined (compose)"
  [[ "$WITH_NGINX" == "true" ]] && echo "  - Nginx configured for ${NGINX_SERVER_NAME}"
  echo
  echo "Next:"
  echo "  • Run syscheck:   sudo $0 syscheck"
  echo "  • Public check (via Nginx, if configured):"
  echo "      curl -s http://${NGINX_SERVER_NAME}/info | jq ."
  echo "  • Local API:      curl -s http://127.0.0.1:${api_port}/health | jq ."
  echo
}

# ------------------------------ SYSCHECK --------------------------------
syscheck_cmd() {
  # Load env if exists
  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
  local api_port="${API_PORT:-$(choose_free_port)}"
  local host="${API_HOST:-$API_HOST_DEFAULT}"
  local public=""
  [[ -n "${NGINX_SERVER_NAME:-}" ]] && public="$NGINX_SERVER_NAME"
  syscheck_block "$host" "$api_port" "$public" || exit 1
}

# ------------------------------ REPAIR ----------------------------------
repair_cmd() {
  info "Stopping any previous compose/app …"
  compose_down || true

  # Ensure env essentials exist & pick free API port if busy
  [[ -f "$ENV_FILE" ]] || touch "$ENV_FILE"
  source "$ENV_FILE" || true
  local api_port="${API_PORT:-$(choose_free_port)}"
  if ss -ltn | awk '{print $4}' | grep -q ":${api_port}$"; then
    api_port="$(choose_free_port)"
    warn "API port busy; switching to ${api_port}"
  fi
  persist_env_kv "API_PORT" "$api_port"

  # Ensure venv & hf cli
  python3 -m venv "$VENV_DIR" 2>/dev/null || true
  "${VENV_DIR}/bin/pip" -q install --upgrade pip wheel setuptools "huggingface_hub[cli]>=0.22" || true

  # Ensure model
  download_model_if_needed "${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf" || true

  # Re-write compose (in case of drift)
  write_compose

  # (Re)start API service
  sysd_reload_enable_restart "swarm-api.service"

  # Bring up agents
  compose_up

  # Repair Nginx (if site exists or if WITH_NGINX requested before)
  if have nginx; then
    [[ -z "${NGINX_SERVER_NAME:-}" ]] && NGINX_SERVER_NAME="$(hostname -I | awk '{print $1}')"
    write_nginx_map
    write_nginx_site "$NGINX_SERVER_NAME" "$api_port"
  fi

  echo "==> Smoke checks"
  sleep 2
  curl -fsS "http://127.0.0.1:${api_port}/health" || true; echo
  for p in 8080 8081 8082 8083; do
    echo -n "llama server port $p ... "
    if curl -fsS "http://127.0.0.1:$p/health" >/dev/null 2>&1; then echo OK; else echo FAIL; fi
  done
  [[ -n "${NGINX_SERVER_NAME:-}" ]] && { echo -n "Public /info via Nginx ... "; curl -fsS "http://${NGINX_SERVER_NAME}/info" || true; echo; }

  echo "Repair complete."
}

# ------------------------------ Dispatcher ------------------------------
case "$cmd" in
  install)  install_cmd;;
  syscheck) syscheck_cmd;;
  repair)   repair_cmd;;
  *) fail "Unknown subcommand: $cmd"; exit 2;;
esac
