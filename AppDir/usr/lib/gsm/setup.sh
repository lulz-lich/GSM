#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_CONFIG_DIR="$HOME/.config/gsm"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
USER_AUTOSTART_DIR="$HOME/.config/autostart"

echo "[GSM] Installing dependencies..."
sudo pacman -S --needed ludusavi rclone python-gobject gtk3 zenity

echo "[GSM] Creating directories..."
mkdir -p "$USER_CONFIG_DIR"
mkdir -p "$HOME/.local/state/gsm"
mkdir -p "$HOME/.cache/gsm/tmp"
mkdir -p "$HOME/.cache/gsm/restore"
mkdir -p "$HOME/game-backups"

echo "[GSM] Installing config..."
if [ ! -f "$USER_CONFIG_DIR/config.toml" ]; then
    cp "$REPO_DIR/config/config.toml" "$USER_CONFIG_DIR/config.toml"
    echo "[GSM] Default config.toml installed."
else
    echo "[GSM] Existing config.toml found. Keeping user config."
fi

echo "[GSM] Installing systemd units..."
mkdir -p "$USER_SYSTEMD_DIR"
sed "s|%h/gsm|$REPO_DIR|g" "$REPO_DIR/systemd/gsm.service" > "$USER_SYSTEMD_DIR/gsm.service"
cp "$REPO_DIR/systemd/gsm.timer" "$USER_SYSTEMD_DIR/gsm.timer"

systemctl --user daemon-reload
systemctl --user enable --now gsm.timer

echo "[GSM] Installing autostart entry..."
mkdir -p "$USER_AUTOSTART_DIR"
cp "$REPO_DIR/desktop/gsm.desktop" "$USER_AUTOSTART_DIR/gsm.desktop"

echo "[GSM] Setting executable permissions..."
chmod +x "$REPO_DIR/src/core/config.sh"
chmod +x "$REPO_DIR/src/gsm_cli.sh"
chmod +x "$REPO_DIR/src/gsm_tui.sh"
chmod +x "$REPO_DIR/src/gsm_gui.py"

echo
echo "[GSM] Setup complete."
echo "[GSM] Automatic scheduled backups are enabled through systemd."
echo "[GSM] Cloud backup library sync and restore are manual actions."
echo "[GSM] Review your config at: $USER_CONFIG_DIR/config.toml"
