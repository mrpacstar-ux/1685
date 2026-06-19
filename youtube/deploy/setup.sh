#!/usr/bin/env bash
# One-shot VPS setup for the Pale Blue Mind autopilot.
# Run as a sudo-capable user on Ubuntu/Debian from inside the repo:
#   cd youtube/deploy && ./setup.sh
# Re-running is safe — it preserves your .env and produced-topic history.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # .../youtube/deploy
APP_SRC="$(cd "$SRC_DIR/.." && pwd)"                     # .../youtube
APP_DIR=/opt/palebluemind
APP_USER=palebluemind

echo "==> Installing Node.js 20 + ffmpeg"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
command -v ffmpeg >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y ffmpeg; }
command -v rsync  >/dev/null 2>&1 || sudo apt-get install -y rsync

echo "==> Creating service user + app dir ($APP_DIR)"
id -u "$APP_USER" >/dev/null 2>&1 || \
  sudo useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
sudo mkdir -p "$APP_DIR"

echo "==> Copying app files (preserving .env + state/history.json)"
sudo rsync -a \
  --exclude node_modules --exclude out \
  --exclude '.env' --exclude 'state/history.json' \
  "$APP_SRC"/ "$APP_DIR"/

# Seed secrets + history only on first install.
[ -f "$APP_DIR/.env" ] || sudo cp "$APP_SRC/.env.example" "$APP_DIR/.env"
sudo mkdir -p "$APP_DIR/state"
[ -f "$APP_DIR/state/history.json" ] || echo '[]' | sudo tee "$APP_DIR/state/history.json" >/dev/null

sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"
sudo chmod 600 "$APP_DIR/.env"

echo "==> Installing npm dependencies"
cd "$APP_DIR"
sudo -u "$APP_USER" HOME="$APP_DIR" npm ci

echo "==> Installing systemd service + timer"
sudo cp "$SRC_DIR/palebluemind-autopilot.service" /etc/systemd/system/
sudo cp "$SRC_DIR/palebluemind-autopilot.timer"   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable palebluemind-autopilot.timer

cat <<EOF

==> DONE.
  1. Add your keys:       sudo nano $APP_DIR/.env
  2. Test one run:        sudo systemctl start palebluemind-autopilot.service
                          journalctl -u palebluemind-autopilot -f
  3. Start the schedule:  sudo systemctl start palebluemind-autopilot.timer
  4. Verify the schedule: systemctl list-timers palebluemind-autopilot.timer
EOF
