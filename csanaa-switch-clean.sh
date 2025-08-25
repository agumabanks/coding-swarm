#!/usr/bin/env bash
# csanaa-switch-clean.sh — make 'sanaa' the canonical CLI (quiet), keep 'swarm' as a silent symlink.
set -euo pipefail

# ---- paths (adapt to your layout if different) ----
INSTALL_DIR="${INSTALL_DIR:-/opt/coding-swarm}"
BIN_DIR="${BIN_DIR:-${INSTALL_DIR}/bin}"
ENV_FILE="${ENV_FILE:-/etc/coding-swarm/cswarm.env}"

SWARM_WRAPPER="${BIN_DIR}/swarm"              # the existing CLI wrapper created by your installer
SANAA_BIN="/usr/local/bin/sanaa"
SANAA_AI_BIN="/usr/local/bin/sanaa.ai"
SWARM_BIN="/usr/local/bin/swarm"

# ---- sanity checks ----
if [[ ! -x "$SWARM_WRAPPER" ]]; then
  echo "❌ Can't find swarm wrapper at: $SWARM_WRAPPER"
  echo "   Ensure your install created ${BIN_DIR}/swarm"
  exit 1
fi

# ---- ensure env file is readable (don't die if it has blanks) ----
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set +u; source "$ENV_FILE" || true; set -u
fi

# ---- create the quiet 'sanaa' shim that just execs the existing swarm wrapper ----
mkdir -p /usr/local/bin
cat >"$SANAA_BIN" <<'SH'
#!/usr/bin/env bash
# quiet shim: forward everything to the installed swarm wrapper
exec /opt/coding-swarm/bin/swarm "$@"
SH
chmod +x "$SANAA_BIN"

# convenience alias
ln -sf "$SANAA_BIN" "$SANAA_AI_BIN"

# ---- make 'swarm' a silent symlink to 'sanaa' (no more spammy notices) ----
# If /usr/local/bin/swarm is a regular script that prints notices, replace it.
if [[ -e "$SWARM_BIN" && ! -L "$SWARM_BIN" ]]; then
  # keep a backup just in case
  cp -f "$SWARM_BIN" "${SWARM_BIN}.bak.$(date +%Y%m%d%H%M%S)" || true
fi
ln -sf "$SANAA_BIN" "$SWARM_BIN"

# ---- OPTIONAL: register with update-alternatives (lets you switch cleanly if you ever need to) ----
if command -v update-alternatives >/dev/null 2>&1; then
  # register sanaa as the 'sanaa' command provider
  sudo update-alternatives --quiet --install /usr/bin/sanaa sanaa "$SANAA_BIN" 50 || true
  # and as 'swarm' provider (so both names resolve to same tool)
  sudo update-alternatives --quiet --install /usr/bin/swarm swarm "$SWARM_BIN" 50 || true
fi

# ---- systemd alias: sanaa-api.service → swarm-api.service ----
# This lets you use either name without creating/duplicating units.
if systemctl list-unit-files | grep -q '^swarm-api\.service'; then
  sudo ln -sf /etc/systemd/system/swarm-api.service /etc/systemd/system/sanaa-api.service
  sudo systemctl daemon-reload
fi

# ---- print result ----
echo "✓ 'sanaa' installed globally at $SANAA_BIN (alias: sanaa.ai)"
echo "✓ 'swarm' now symlinks quietly to 'sanaa' at $SWARM_BIN"
if systemctl list-units --type=service | grep -q 'swarm-api'; then
  echo "✓ systemd: you can use 'sudo systemctl restart sanaa-api' (aliases swarm-api)"
fi

echo
echo "Use it like:"
echo "  sanaa --help"
echo "  sanaa run --goal \"Add auth\" --project /path/to/repo"
echo "  sanaa chat --project /home/swarm/projects/sanaa-website --mode debug"
echo "  sanaa task -g \"Fix build\" -p /home/swarm/projects/sanaa-website --mode code --commit --push"
