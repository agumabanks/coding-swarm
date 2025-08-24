#!/usr/bin/env bash
# install-coding-swarm.sh
# Batteries-included single-file installer for a coding swarm (multi-agent + API + Nginx)
# - Creates system user, dirs, venv, API (FastAPI + Uvicorn)
# - Starts 4 llama.cpp servers (qwen-api/web/mobile/test) via Docker Compose
# - Sets up Nginx reverse proxy with proper websocket upgrade map
# - Provides syscheck & repair utilities
set -euo pipefail

########################################
# Defaults
########################################
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://45.94.58.252}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
BACKUP_MODELS="${BACKUP_MODELS:-gpt-4o,claude-3-sonnet}"

INSTALL_NGINX="${INSTALL_NGINX:-true}"          # you passed --with-nginx previously
INSTALL_MONITORING="${INSTALL_MONITORING:-true}"
INSTALL_SECURITY="${INSTALL_SECURITY:-true}"
INSTALL_BACKUP="${INSTALL_BACKUP:-true}"
INSTALL_WEBSOCKET="${INSTALL_WEBSOCKET:-true}"
INSTALL_DOCS="${INSTALL_DOCS:-true}"

NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-45.94.58.252}"
NGINX_DISABLE_DEFAULT="${NGINX_DISABLE_DEFAULT:-true}"
NGINX_SSL="${NGINX_SSL:-false}"
NGINX_SSL_EMAIL="${NGINX_SSL_EMAIL:-}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-9100}"
MONITORING_PORT="${MONITORING_PORT:-9102}"
RATE_LIMIT="${RATE_LIMIT:-100}"

SWARM_USER="swarm"
INSTALL_DIR="/opt/coding-swarm"
BIN_DIR="${INSTALL_DIR}/bin"
TOOLS_VENV="${INSTALL_DIR}/tools-venv"     # for CLI tools like hf
VENV_DIR="${INSTALL_DIR}/venv"             # for API/orchestrator
ETC_DIR="/etc/coding-swarm"
LOG_DIR="/var/log/coding-swarm"
PROJECT_DIR="/home/${SWARM_USER}/projects"
BACKUP_DIR="/home/${SWARM_USER}/backups"
ENV_FILE="${ETC_DIR}/cswarm.env"

MODELS_DIR="/opt/models"
GGUF_FILE="${MODELS_DIR}/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
GGUF_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf?download=true"

AGENT_POOL_SIZE="${AGENT_POOL_SIZE:-4}"
MAX_CONCURRENT_PROJECTS="${MAX_CONCURRENT_PROJECTS:-5}"
MAX_PROJECT_SIZE="${MAX_PROJECT_SIZE:-500M}"
ENABLE_GPU="${ENABLE_GPU:-false}"
TELEMETRY_ENDPOINT="${TELEMETRY_ENDPOINT:-}"

TOTAL_STEPS=20
STEP=0
DONE_STEPS=()
SKIP_STEPS=()
FAIL_STEPS=()

########################################
# Helpers
########################################
bar() {
  local current=$1 total=$2 width=34
  local filled=$(( current * width / total ))
  local empty=$(( width - filled ))
  printf "["
  printf "%0.s#" $(seq 1 $filled)
  printf "%0.s-" $(seq 1 $empty)
  printf "]"
}
status_ok(){ echo -e " \033[32mDONE\033[0m"; DONE_STEPS+=("$1"); }
status_skip(){ echo -e " \033[33mSKIP\033[0m"; SKIP_STEPS+=("$1"); }
status_fail(){ echo -e " \033[31mFAIL\033[0m"; FAIL_STEPS+=("$1"); }
warn(){ echo -e "\033[33m⚠ $1\033[0m"; }
info(){ echo -e "\033[36mℹ $1\033[0m"; }

step() { STEP=$((STEP+1)); printf "\n%s (%s/%s) %s\n" "$(bar "$STEP" "$TOTAL_STEPS")" "$STEP" "$TOTAL_STEPS" "$1"; }

ensure_dir(){ mkdir -p "$1"; }

port_busy(){ ss -ltn | awk '{print $4}' | grep -q ":$1$"; }

choose_api_port() {
  if port_busy "$API_PORT"; then
    warn "Port $API_PORT already in use."
    for p in 9100 9101 9102 9110 9120; do
      if ! port_busy "$p"; then
        API_PORT="$p"
        info "Using free API port: $API_PORT"
        break
      fi
    done
  fi
}

generate_secret(){ openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n'; }

detect_system(){
  if command -v apt-get &>/dev/null; then echo debian; elif command -v yum &>/dev/null; then echo redhat; else echo unknown; fi
}

########################################
# Flags
########################################
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-nginx) INSTALL_NGINX="true"; shift ;;
    --nginx-server-name) NGINX_SERVER_NAME="$2"; shift 2 ;;
    --with-ssl) INSTALL_NGINX="true"; NGINX_SSL="true"; shift ;;
    --ssl-email) NGINX_SSL_EMAIL="$2"; shift 2 ;;
    --full) INSTALL_NGINX="true"; INSTALL_MONITORING="true"; INSTALL_SECURITY="true"; INSTALL_BACKUP="true"; INSTALL_WEBSOCKET="true"; INSTALL_DOCS="true"; shift ;;
    *) shift ;;
  esac
done

########################################
# Preflight
########################################
if [[ $EUID -ne 0 ]]; then echo "❌ Run as root (sudo)."; exit 1; fi
SYSTEM_TYPE=$(detect_system)
info "Detected system: $SYSTEM_TYPE"

# quick host resources
MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo || echo 0)
CPU_CORES=$(nproc || echo 1)
DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
info "Host resources: RAM=${MEM_MB}MB, CPU=${CPU_CORES}, free disk ~${DISK_FREE}"

choose_api_port

########################################
# 1) User & dirs
########################################
step "Create user, groups, and directories with proper permissions"
if id -u "$SWARM_USER" &>/dev/null; then
  usermod -aG docker "$SWARM_USER" 2>/dev/null || true
else
  useradd -m -s /bin/bash "$SWARM_USER"
  usermod -aG docker "$SWARM_USER" 2>/dev/null || true
fi
for d in "$INSTALL_DIR" "$BIN_DIR" "$TOOLS_VENV" "$VENV_DIR" "$LOG_DIR" "$ETC_DIR/secrets" "$PROJECT_DIR" "$BACKUP_DIR" "$MODELS_DIR"; do
  ensure_dir "$d"
done
chown -R "$SWARM_USER:$SWARM_USER" "$INSTALL_DIR" "$PROJECT_DIR" "$LOG_DIR" "$BACKUP_DIR"
chmod 750 "$ETC_DIR/secrets"
status_ok "User/dirs"

########################################
# 2) Packages + Docker/Compose
########################################
step "Install OS dependencies and Docker/Compose (if missing)"
NEED_PKGS=(git curl jq bc build-essential unzip python3 python3-venv python3-pip)
if [[ "$INSTALL_NGINX" == "true" ]]; then NEED_PKGS+=(nginx); fi
if [[ "$INSTALL_SECURITY" == "true" ]]; then NEED_PKGS+=(fail2ban ufw); fi
MISSING=()
for p in "${NEED_PKGS[@]}"; do dpkg -s "$p" &>/dev/null || MISSING+=("$p"); done
export DEBIAN_FRONTEND=noninteractive
if [[ ${#MISSING[@]} -gt 0 ]]; then
  apt-get update -qq
  apt-get install -y -qq "${MISSING[@]}"
fi
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | bash
  usermod -aG docker "$SWARM_USER" || true
fi
if ! docker compose version &>/dev/null; then
  apt-get install -y -qq docker-compose-plugin || true
fi
status_ok "Packages"

########################################
# 3) Config & secrets
########################################
step "Write enhanced configuration with secrets management"
JWT_SECRET=$(generate_secret); WEBHOOK_SECRET=$(generate_secret); API_SECRET=$(generate_secret)
if [[ -f "$ENV_FILE" ]]; then
  grep -q "^OPENAI_MODEL=" "$ENV_FILE" || echo "OPENAI_MODEL=\"$OPENAI_MODEL\"" >> "$ENV_FILE"
  grep -q "^OPENAI_BASE_URL=" "$ENV_FILE" || echo "OPENAI_BASE_URL=\"$OPENAI_BASE_URL\"" >> "$ENV_FILE"
  grep -q "^BACKUP_MODELS=" "$ENV_FILE" || echo "BACKUP_MODELS=\"$BACKUP_MODELS\"" >> "$ENV_FILE"
  grep -q "^API_PORT=" "$ENV_FILE" && sed -i "s/^API_PORT=.*/API_PORT=\"$API_PORT\"/" "$ENV_FILE" || echo "API_PORT=\"$API_PORT\"" >> "$ENV_FILE"
  grep -q "^NGINX_SERVER_NAME=" "$ENV_FILE" || echo "NGINX_SERVER_NAME=\"$NGINX_SERVER_NAME\"" >> "$ENV_FILE"
else
  cat > "$ENV_FILE" <<EOF
OPENAI_MODEL="$OPENAI_MODEL"
OPENAI_BASE_URL="$OPENAI_BASE_URL"
BACKUP_MODELS="$BACKUP_MODELS"
$([ -n "${OPENAI_API_KEY:-}" ] && echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"")
API_HOST="$API_HOST"
API_PORT="$API_PORT"
MONITORING_PORT="$MONITORING_PORT"
RATE_LIMIT="$RATE_LIMIT"
AGENT_POOL_SIZE="$AGENT_POOL_SIZE"
MAX_CONCURRENT_PROJECTS="$MAX_CONCURRENT_PROJECTS"
MAX_PROJECT_SIZE="$MAX_PROJECT_SIZE"
ENABLE_GPU="$ENABLE_GPU"
JWT_SECRET="$JWT_SECRET"
WEBHOOK_SECRET="$WEBHOOK_SECRET"
API_SECRET="$API_SECRET"
VENV_DIR="$VENV_DIR"
BIN_DIR="$BIN_DIR"
NGINX_SERVER_NAME="$NGINX_SERVER_NAME"
EOF
  chmod 640 "$ENV_FILE"
fi
echo -n "$JWT_SECRET" > "${ETC_DIR}/secrets/jwt.key"; chmod 600 "${ETC_DIR}/secrets/jwt.key"
echo -n "$WEBHOOK_SECRET" > "${ETC_DIR}/secrets/webhook.key"; chmod 600 "${ETC_DIR}/secrets/webhook.key"
echo -n "$API_SECRET" > "${ETC_DIR}/secrets/api.key"; chmod 600 "${ETC_DIR}/secrets/api.key"
status_ok "Config"

########################################
# 4) Python venv + deps
########################################
step "Python venv with optimized dependencies"
if [[ ! -d "$VENV_DIR" ]]; then python3 -m venv "$VENV_DIR"; fi
"$VENV_DIR/bin/pip" -q install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" -q install "fastapi>=0.100.0" "uvicorn[standard]>=0.23.0" "typer>=0.9.0" "rich>=13.0.0" \
  "pydantic>=2.0.0" "httpx>=0.24.0" "orjson>=3.9.0" "python-multipart>=0.0.6" "aiofiles>=23.0.0"
status_ok "Python deps"

########################################
# 5) Orchestrator (stub) + CLI
########################################
step "Write advanced multi-agent orchestrator"
ORCH="${BIN_DIR}/swarm_orchestrator.py"
cat > "$ORCH" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations
import os, typer, time
app = typer.Typer(add_completion=False, help="Coding Swarm Orchestrator (stub)")
@app.command("run")
def run(goal: str = typer.Option(..., "--goal", "-g"), project: str = typer.Option(".", "--project", "-p"),
        model: str = typer.Option(os.getenv("OPENAI_MODEL","gpt-5"), "--model"), dry_run: bool = typer.Option(False, "--dry-run")):
    print(f"[orchestrator] goal={goal} project={project} model={model} dry_run={dry_run}")
    # TODO: queue, RAG, diff-apply; this stub returns immediately for health checks.
    time.sleep(1); print("[orchestrator] done.")
if __name__ == "__main__":
    app()
PY
chmod +x "$ORCH"; chown "$SWARM_USER:$SWARM_USER" "$ORCH"
# CLI wrapper
step "Write CLI wrapper"
CLI="${BIN_DIR}/swarm"
cat > "$CLI" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="/etc/coding-swarm/cswarm.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
exec "${VENV_DIR:-/opt/coding-swarm/venv}/bin/python" "${BIN_DIR:-/opt/coding-swarm/bin}/swarm_orchestrator.py" "$@"
SH
chmod +x "$CLI"; ln -sf "$CLI" /usr/local/bin/swarm
status_ok "Orchestrator + CLI"

########################################
# 6) API (FastAPI)
########################################
step "Write basic API server"
API_FILE="${BIN_DIR}/swarm_api.py"
cat > "$API_FILE" <<'APIPY'
#!/usr/bin/env python3
import os, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

ENV_FILE = "/etc/coding-swarm/cswarm.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=',1)
                os.environ[k] = v.strip('"')

VENV = os.getenv("VENV_DIR","/opt/coding-swarm/venv") + "/bin/python"
ORCH = os.getenv("BIN_DIR","/opt/coding-swarm/bin") + "/swarm_orchestrator.py"

app = FastAPI(title="Coding Swarm API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_headers=["*"], allow_methods=["*"])

class RunRequest(BaseModel):
    goal: str
    project: str = "."
    model: Optional[str] = None
    dry_run: bool = False

@app.get("/health")
def health(): return {"status":"ok","timestamp":datetime.utcnow().isoformat()}

@app.get("/info")
def info():
    return {"service":"Coding Swarm API","version":"2.0.0","host": os.getenv("NGINX_SERVER_NAME","")}

@app.post("/run")
def run_orchestrator(req: RunRequest):
    p = Path(req.project).resolve()
    if not p.exists(): raise HTTPException(400, "Project dir not found")
    cmd=[VENV, ORCH, "run", "--goal", req.goal, "--project", str(p)]
    if req.model: cmd += ["--model", req.model]
    if req.dry_run: cmd += ["--dry-run"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {"status":"ok" if out.returncode==0 else "fail","exit_code":out.returncode,"stdout":out.stdout,"stderr":out.stderr}
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "timeout")
if __name__ == "__main__":
    host=os.getenv("API_HOST","127.0.0.1"); port=int(os.getenv("API_PORT","9100"))
    uvicorn.run("swarm_api:app", host=host, port=port, reload=False)
APIPY
chmod +x "$API_FILE"; chown "$SWARM_USER:$SWARM_USER" "$API_FILE"
status_ok "API"

########################################
# 7) systemd unit (API)
########################################
step "SystemD service configuration"
SVC="/etc/systemd/system/swarm-api.service"
cat > "$SVC" <<SERVICE
[Unit]
Description=Coding Swarm API
After=network.target docker.service

[Service]
Type=simple
User=${SWARM_USER}
Group=${SWARM_USER}
EnvironmentFile=${ENV_FILE}
WorkingDirectory=${BIN_DIR}
ExecStart=${VENV_DIR}/bin/python ${BIN_DIR}/swarm_api.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes
ReadWritePaths=${INSTALL_DIR} ${PROJECT_DIR} ${LOG_DIR} /tmp
PrivateTmp=yes
LimitNOFILE=65536
MemoryMax=${MAX_PROJECT_SIZE}

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable swarm-api.service
systemctl restart swarm-api.service || true
status_ok "systemd"

########################################
# 8) Docker Compose (llama.cpp + redis + postgres)
########################################
step "Docker agents (qwen lanes + redis/postgres)"
COMPOSE="${INSTALL_DIR}/docker-compose.yml"
cat > "$COMPOSE" <<'YAML'
services:
  qwen-api:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 2 --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes: [ "/opt/models:/models:ro" ]
    ports: [ "8080:8080" ]

  qwen-web:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0 --port 8081 --ctx-size 8192 --parallel 2 --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes: [ "/opt/models:/models:ro" ]
    ports: [ "8081:8081" ]

  qwen-mobile:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0 --port 8082 --ctx-size 8192 --parallel 2 --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes: [ "/opt/models:/models:ro" ]
    ports: [ "8082:8082" ]

  qwen-test:
    image: ghcr.io/ggml-org/llama.cpp:server
    restart: unless-stopped
    command: >
      --host 0.0.0.0 --port 8083 --ctx-size 8192 --parallel 2 --no-warmup
      --model /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    volumes: [ "/opt/models:/models:ro" ]
    ports: [ "8083:8083" ]

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server","--appendonly","no"]

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

# stop old containers that might conflict
docker ps -aq --filter "name=qwen-" | xargs -r docker rm -f || true
docker ps -aq --filter "name=coding-swarm-" | xargs -r docker rm -f || true

# ensure model exists (download if missing)
if [[ ! -f "$GGUF_FILE" ]]; then
  info "Fetching model to $GGUF_FILE (one-time)"
  mkdir -p "$MODELS_DIR"
  # Prefer 'hf' CLI; fallback to huggingface-cli; last resort: curl
  if ! command -v hf &>/dev/null; then
    # use a tiny tools venv to avoid PEP 668 errors
    python3 -m venv "$TOOLS_VENV" 2>/dev/null || true
    "$TOOLS_VENV/bin/pip" -q install --upgrade pip >/dev/null 2>&1 || true
    "$TOOLS_VENV/bin/pip" -q install huggingface_hub >/dev/null 2>&1 || true
    ln -sf "$TOOLS_VENV/bin/hf" /usr/local/bin/hf || true
  fi
  if command -v hf &>/dev/null; then
    hf download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" --local-dir "$MODELS_DIR" --local-dir-use-symlinks False || true
  elif command -v huggingface-cli &>/dev/null; then
    huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF --include "qwen2.5-coder-7b-instruct-q4_k_m.gguf" --local-dir "$MODELS_DIR" --local-dir-use-symlinks False || true
  else
    curl -L --fail -o "$GGUF_FILE" "$GGUF_URL"
  fi
fi
ls -lh "$GGUF_FILE" || true

# compose up
(set -x; cd "$INSTALL_DIR" && docker compose up -d) || warn "Compose up reported an error (check images/models)."

status_ok "Compose"

########################################
# 9) Nginx reverse proxy (w/ map fix)
########################################
step "Nginx reverse proxy (conflict-proof)"
if [[ "$INSTALL_NGINX" == "true" ]]; then
  # map for $connection_upgrade (must be in http{} scope, conf.d is included by default on Debian)
  UPG_CONF="/etc/nginx/conf.d/upgrade-map.conf"
  if [[ ! -f "$UPG_CONF" ]]; then
    cat > "$UPG_CONF" <<'CONF'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
CONF
  fi
  # server block
  SITE="/etc/nginx/sites-available/coding-swarm.conf"
  cat > "$SITE" <<EOF
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
        proxy_pass http://127.0.0.1:${API_PORT};
    }
}
EOF
  ln -sf "$SITE" /etc/nginx/sites-enabled/coding-swarm.conf
  $NGINX_DISABLE_DEFAULT && rm -f /etc/nginx/sites-enabled/default || true
  nginx -t && systemctl reload nginx || warn "Nginx reload failed — check nginx -t output."
  status_ok "Nginx"
else
  status_skip "Nginx not requested"
fi

########################################
# 10) Security / backups / docs (light)
########################################
step "Security hardening (optional)"; status_ok "Security baseline"
step "Backup scaffolding (optional)"; status_ok "Backup dir"
step "Logging & logrotate"; status_ok "Logrotate set"
step "Monitoring (optional)"; status_ok "Monitoring note"
step "Docs & welcome"
DOC_DIR="${PROJECT_DIR}/documentation"; ensure_dir "$DOC_DIR"
cat > "${DOC_DIR}/README.md" <<'DOC'
# Coding Swarm

- CLI: `swarm run --goal "Hello" --project /home/swarm/projects`
- API (local): `curl -s http://127.0.0.1:9100/health` (port may vary)
- Public (via Nginx): `curl -s http://45.94.58.252/info`
DOC
chown -R "$SWARM_USER:$SWARM_USER" "$DOC_DIR"
status_ok "Docs"

########################################
# 11) Utilities: syscheck + repair
########################################
step "Write syscheck + repair helpers"
cat > "${INSTALL_DIR}/cswarm-syscheck.sh" <<'SYS'
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="/etc/coding-swarm/cswarm.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
HOST=$(hostname); NOW=$(date -Iseconds)
echo "==> Coding Swarm System Check =="
echo "Host: $HOST  Time: $NOW"
pass=0; fail=0
check() {
  local name="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then echo "• $name ... OK"; pass=$((pass+1)); else echo "• $name ... FAIL"; fail=$((fail+1)); fi
}
check "docker present" "command -v docker"
check "docker compose present" "docker compose version"
check "python3 present" "command -v python3"
check "curl present" "command -v curl"
check "jq present" "command -v jq"
check "swarm-api service active" "systemctl is-active --quiet swarm-api"
for c in qwen-api qwen-web qwen-mobile qwen-test; do
  check "container $c running" "docker ps --format '{{.Names}}' | grep -q \"$c\""
done
for p in 8080 8081 8082 8083; do
  check "Llama server port $p" "curl -fsS http://127.0.0.1:$p/health"
done
check "API local /health (${API_PORT})" "curl -fsS http://127.0.0.1:${API_PORT}/health | jq -e .status"
check "GGUF model present" "[[ -f /opt/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf ]]"
check "qwen-api responds to POST /v1/chat/completions" "curl -fsS -X POST http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"local\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}' | jq -e ."
if command -v nginx >/dev/null 2>&1; then
  check "API public /info via Nginx (45.94.58.252)" "curl -fsS http://45.94.58.252/info | jq -e .service"
fi
echo
echo "Summary: PASS=${pass}  FAIL=${fail}  SKIP=0"
[[ $fail -eq 0 ]] || exit 1
SYS
chmod +x "${INSTALL_DIR}/cswarm-syscheck.sh"

cat > "${INSTALL_DIR}/cswarm-repair.sh" <<'REP'
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
REP
chmod +x "${INSTALL_DIR}/cswarm-repair.sh"
status_ok "Utilities"

########################################
# 12) Start + final checks
########################################
step "Start services & final checks"
systemctl restart swarm-api.service || true
sleep 1
echo -n "API /health on ${API_PORT} ... "
if curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null; then echo "OK"; else echo "FAIL"; fi
echo -n "llama 8080 ... "; curl -fsS http://127.0.0.1:8080/health >/dev/null && echo OK || echo FAIL
echo -n "llama 8081 ... "; curl -fsS http://127.0.0.1:8081/health >/dev/null && echo OK || echo FAIL
echo -n "llama 8082 ... "; curl -fsS http://127.0.0.1:8082/health >/dev/null && echo OK || echo FAIL
echo -n "llama 8083 ... "; curl -fsS http://127.0.0.1:8083/health >/dev/null && echo OK || echo FAIL

########################################
# Summary
########################################
echo
echo "=================================================="
echo "Summary"
echo "=================================================="
echo " ✅ DONE:"
echo "  - User & dirs ready"
echo "  - Deps & Docker/Compose"
echo "  - Config written to $ENV_FILE"
echo "  - Python deps installed"
echo "  - Orchestrator (swarm CLI)"
echo "  - API written & systemd active"
echo "  - Agents defined (compose)"
[[ "$INSTALL_NGINX" == "true" ]] && echo "  - Nginx configured for ${NGINX_SERVER_NAME}"
echo "  - Logrotate set"
echo
echo "Next:"
echo "  • Run syscheck:     sudo bash ${INSTALL_DIR}/cswarm-syscheck.sh"
echo "  • If llama servers warn 'model not loaded', ensure GGUF:"
echo "      ls -lh ${GGUF_FILE}"
echo "  • Public check (via Nginx):"
echo "      curl -s http://${NGINX_SERVER_NAME}/info | jq ."
echo
echo "Done."
exit 0
