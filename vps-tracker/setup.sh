#!/usr/bin/env bash
# One-shot VPS setup for the KD1685 player-data bot.
# Run as a sudo-capable user on Ubuntu/Debian. Idempotent-ish; re-running is safe.
set -euo pipefail

# Folder this script lives in (where the unit files + app files are)
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APP_DIR=/opt/kd1685-tracker
APP_USER=kd1685

echo "==> Installing Node.js 22 + system deps"
# Node 22 LTS: the current @supabase/supabase-js needs a native global WebSocket,
# which Node < 22 lacks (it throws at createClient). 22 has it built in.
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "==> Creating service user + app dir"
id -u "$APP_USER" >/dev/null 2>&1 || sudo useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
sudo mkdir -p "$APP_DIR"

echo "==> Copying app files"
sudo cp "$SRC_DIR/sync.js" "$SRC_DIR/package.json" "$APP_DIR"/
[ -f "$APP_DIR/.env" ] || sudo cp "$SRC_DIR/.env.example" "$APP_DIR/.env"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Installing npm deps + Playwright Chromium (with OS libraries)"
cd "$APP_DIR"
sudo -u "$APP_USER" npm install --omit=dev
sudo npx playwright install-deps chromium
sudo -u "$APP_USER" npx playwright install chromium

echo "==> Installing systemd service + timer"
sudo cp "$SRC_DIR/kd1685-sync.service" /etc/systemd/system/kd1685-sync.service
sudo cp "$SRC_DIR/kd1685-sync.timer" /etc/systemd/system/kd1685-sync.timer
sudo systemctl daemon-reload
sudo systemctl enable --now kd1685-sync.timer

echo ""
echo "==> DONE. Now edit secrets:  sudo nano $APP_DIR/.env"
echo "    Then test once:          sudo systemctl start kd1685-sync.service && journalctl -u kd1685-sync -f"
echo "    Check the schedule:      systemctl list-timers kd1685-sync.timer"
