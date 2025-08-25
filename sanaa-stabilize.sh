#!/usr/bin/env bash
set -euo pipefail

# ---- Paths / defaults ----
ENV_FILE=${ENV_FILE:-/etc/coding-swarm/cswarm.env}
INSTALL_DIR=${INSTALL_DIR:-/opt/coding-swarm}
BIN_DIR=${BIN_DIR:-$INSTALL_DIR/bin}
VENV_DIR=${VENV_DIR:-$INSTALL_DIR/venv}
ORCH=${ORCH:-$BIN_DIR/swarm_orchestrator.py}
SERVICE=swarm-api.service

red() { echo -e "\033[31m$*\033[0m"; }
grn() { echo -e "\033[32m$*\033[0m"; }
ylw() { echo -e "\033[33m$*\033[0m"; }
cyan(){ echo -e "\033[36m$*\033[0m"; }

need() { command -v "$1" >/dev/null 2>&1 || { red "missing: $1"; exit 1; }; }
need sed; need awk; need systemctl

# ---- Pick a free API port (prefer 9101) ----
pick_free_port() {
  local cand ports
  ports=("9101" "9102" "9110")
  for cand in "${ports[@]}"; do
    if ! ss -ltnH | awk '{print $4}' | grep -q ":${cand}\$"; then
      echo "$cand"; return
    fi
  done
  echo 9101
}

# ---- Rebuild a safe env file (no ${...} expansions, balanced quotes) ----
rewrite_env() {
  local api_port host
  host=${API_HOST:-127.0.0.1}
  # Try to read old file just to reuse values, but don't trust its quoting
  local old_port=""; [[ -f "$ENV_FILE" ]] && old_port="$(grep -E '^API_PORT=' "$ENV_FILE" 2>/dev/null | sed -E 's/^API_PORT=//;s/"//g;s/'"'"'//g')"
  if [[ -z "${old_port:-}" || ! "$old_port" =~ ^[0-9]+$ ]]; then
    old_port="$(pick_free_port)"
  fi

  umask 022
  sudo install -d -m 755 "$(dirname "$ENV_FILE")"
  sudo cp -a "$ENV_FILE" "${ENV_FILE}.bak.$(date +%s)" 2>/dev/null || true

  sudo tee "$ENV_FILE" >/dev/null <<EOF
# === Sanaa/Coding-Swarm environment (clean) ===
OPENAI_MODEL="gpt-5"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://45.94.58.252}"
BACKUP_MODELS="${BACKUP_MODELS:-gpt-4o,claude-3-sonnet}"

API_HOST="${host}"
API_PORT="${old_port}"
WS_PORT="${WS_PORT:-9101}"
MONITORING_PORT="${MONITORING_PORT:-9102}"

VENV_DIR="${VENV_DIR}"
BIN_DIR="${BIN_DIR}"

# feature flags you already use elsewhere (kept harmless here)
INSTALL_MONITORING="${INSTALL_MONITORING:-true}"
INSTALL_SECURITY="${INSTALL_SECURITY:-true}"
INSTALL_BACKUP="${INSTALL_BACKUP:-true}"
INSTALL_WEBSOCKET="${INSTALL_WEBSOCKET:-true}"
EOF
  sudo chmod 0640 "$ENV_FILE"
  grn "✓ wrote $ENV_FILE"
}

# ---- Write quiet, non-looping launchers ----
write_launchers() {
  sudo tee /usr/local/bin/sanaa >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail
# Load env (quiet)
if [[ -f /etc/coding-swarm/cswarm.env ]]; then set +u; # shellcheck disable=SC1091
  . /etc/coding-swarm/cswarm.env; set -u; fi
PY="${VENV_DIR:-/opt/coding-swarm/venv}/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
ORCH="${BIN_DIR:-/opt/coding-swarm/bin}/swarm_orchestrator.py"
exec "$PY" "$ORCH" "$@"
SH
  sudo chmod +x /usr/local/bin/sanaa

  # Make 'swarm' do the same (no forwarding message to avoid spam)
  sudo tee /usr/local/bin/swarm >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ -f /etc/coding-swarm/cswarm.env ]]; then set +u; # shellcheck disable=SC1091
  . /etc/coding-swarm/cswarm.env; set -u; fi
PY="${VENV_DIR:-/opt/coding-swarm/venv}/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
ORCH="${BIN_DIR:-/opt/coding-swarm/bin}/swarm_orchestrator.py"
exec "$PY" "$ORCH" "$@"
SH
  sudo chmod +x /usr/local/bin/swarm
  grn "✓ installed /usr/local/bin/{sanaa,swarm}"
}

# ---- Restart API and show health ----
restart_api() {
  sudo systemctl daemon-reload || true
  sudo systemctl restart "$SERVICE" || true
  sleep 1
  if systemctl is-active --quiet "$SERVICE"; then
    grn "✓ $SERVICE running"
  else
    ylw "⚠ $SERVICE not active yet; showing last 40 lines:"
    journalctl -u "$SERVICE" -n 40 --no-pager || true
  fi

  # Provide quick health check line
  local port
  port="$(grep -E '^API_PORT=' "$ENV_FILE" | sed -E 's/^API_PORT=//;s/"//g')"
  ylw "Health probe (curl):  http://127.0.0.1:${port}/health"
  curl -fsS "http://127.0.0.1:${port}/health" || true
  echo
}

# ---- sanity checks: llama servers ----
check_llama() {
  local ports=(8080 8081 8082 8083) p ok=0
  for p in "${ports[@]}"; do
    if curl -fsS "http://127.0.0.1:${p}/health" >/dev/null 2>&1; then
      echo "✓ llama server ${p} OK"; ((ok++)) || true
    else
      ylw "△ llama server ${p} not ready"
    fi
  done
  (( ok > 0 )) || ylw "No llama ports responded; your compose may still be warming up."
}

# ---- Run all ----
cyan "== stabilizing env & launchers =="
rewrite_env
write_launchers
restart_api
check_llama

echo
grn "Done. Usage examples:"
echo "  sanaa --goal \"Hello from Sanaa\" --project /tmp --dry-run"
echo "  sanaa --goal \"Add auth\"       --project /home/swarm/projects/myapp"
