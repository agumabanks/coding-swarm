#!/usr/bin/env bash
# sanaa-fix.sh — make 'sanaa' work, fix API port conflicts, and smoke-check.
set -euo pipefail

ENV_FILE="/etc/coding-swarm/cswarm.env"
INSTALL_DIR="/opt/coding-swarm"
BIN_DIR="${INSTALL_DIR}/bin"
ORCH="${BIN_DIR}/swarm_orchestrator.py"
VENV_DIR_DEFAULT="${INSTALL_DIR}/venv"
SITE_AVAIL="/etc/nginx/sites-available/coding-swarm.conf"
SITE_EN="/etc/nginx/sites-enabled/coding-swarm.conf"

notice(){ echo -e "\033[36mℹ $*\033[0m"; }
ok(){ echo -e "\033[32m✓ $*\033[0m"; }
warn(){ echo -e "\033[33m⚠ $*\033[0m"; }
die(){ echo -e "\033[31m✗ $*\033[0m"; exit 1; }

[[ -f "$ORCH" ]] || die "Missing orchestrator at $ORCH"
[[ -d "$INSTALL_DIR" ]] || die "Missing $INSTALL_DIR"

# ---- Load env if present (lenient) ----
if [[ -f "$ENV_FILE" ]]; then
  set +u
  # shellcheck disable=SC1090
  source "$ENV_FILE" || true
  set -u
fi

# ---- Decide a safe API port (avoid 9100: node_exporter) ----
port_free() { ss -ltnH | awk '{print $4}' | grep -q ":$1$" && return 1 || return 0; }
API_PORT_FIX="${API_PORT:-9101}"
if ! port_free "$API_PORT_FIX"; then
  for p in 9101 9102 9110 9120; do
    if port_free "$p"; then API_PORT_FIX="$p"; break; fi
  done
fi
[[ "$API_PORT_FIX" =~ ^[0-9]+$ ]] || API_PORT_FIX=9101

# ---- Make sure ENV file is sane (no bash substitutions, just literal numbers/strings) ----
sudo install -d -m 0750 "$(dirname "$ENV_FILE")"
if [[ -f "$ENV_FILE" ]]; then
  sudo sed -i \
    -e 's/^API_PORT=.*/API_PORT="'"$API_PORT_FIX"'"/' \
    -e 's/^[[:space:]]*$//' \
    "$ENV_FILE"
  if ! grep -q '^API_PORT=' "$ENV_FILE"; then
    echo "API_PORT=\"$API_PORT_FIX\"" | sudo tee -a "$ENV_FILE" >/dev/null
  fi
else
  cat | sudo tee "$ENV_FILE" >/dev/null <<EOF
API_PORT="$API_PORT_FIX"
API_HOST="127.0.0.1"
VENV_DIR="$VENV_DIR_DEFAULT"
BIN_DIR="$BIN_DIR"
EOF
  sudo chmod 0640 "$ENV_FILE"
fi
ok "ENV ready (API_PORT=$API_PORT_FIX)"

# ---- Create a clean 'sanaa' launcher (no /bin/python, no hidden loops) ----
sudo tee /usr/local/bin/sanaa >/dev/null <<'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="/etc/coding-swarm/cswarm.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

# prefer venv python if available, else python3
PY="${VENV_DIR:-/opt/coding-swarm/venv}/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

ORCH="${BIN_DIR:-/opt/coding-swarm/bin}/swarm_orchestrator.py"
if [[ ! -f "$ORCH" ]]; then
  echo "Orchestrator not found at $ORCH" >&2; exit 2
fi

# NOTE: current orchestrator expects direct options (no 'run' subcommand)
exec "$PY" "$ORCH" "$@"
LAUNCH
sudo chmod +x /usr/local/bin/sanaa
ok "Installed /usr/local/bin/sanaa"

# Optional convenience alias
sudo ln -sf /usr/local/bin/sanaa /usr/local/bin/sanaa.ai || true

# ---- Make a silent one-shot 'swarm' forwarder (no recursion, no spam) ----
sudo tee /usr/local/bin/swarm >/dev/null <<'FWD'
#!/usr/bin/env bash
exec /usr/local/bin/sanaa "$@"
FWD
sudo chmod +x /usr/local/bin/swarm
ok "Forwarder /usr/local/bin/swarm → sanaa"

# ---- Restart API service on the new port ----
sudo systemctl daemon-reload || true
sudo systemctl restart swarm-api.service || true
sleep 1

# ---- Quick health checks ----
notice "API /health on ${API_PORT_FIX}:"
if curl -fsS "http://127.0.0.1:${API_PORT_FIX}/health" ; then
  ok "API reachable on ${API_PORT_FIX}"
else
  warn "API not responding on ${API_PORT_FIX} (will still finish; check 'journalctl -u swarm-api -n 80')"
fi

for p in 8080 8081 8082 8083; do
  if curl -fsS "http://127.0.0.1:$p/health" >/dev/null 2>&1; then
    ok "llama server $p OK"
  else
    warn "llama server $p not ready"
  fi
done

echo
echo "Done. Use: sanaa --goal \"...\" --project /path [--dry-run] [--model MODEL]"
