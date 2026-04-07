#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_CONFIG_DIR="$HOME/.config/gsm"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
USER_AUTOSTART_DIR="$HOME/.config/autostart"

if ! command -v pacman >/dev/null 2>&1; then
    echo "[GSM] This setup script currently targets Arch Linux / pacman."
    exit 1
fi

echo "[GSM] Installing dependencies..."
sudo pacman -S --needed ludusavi rclone python-gobject gtk3 zenity

echo "[GSM] Creating directories..."
mkdir -p "$USER_CONFIG_DIR"
mkdir -p "$HOME/.local/state/gsm"
mkdir -p "$HOME/.cache/gsm/tmp"
mkdir -p "$HOME/.cache/gsm/restore"
mkdir -p "$HOME/game-backups"

echo "[GSM] Installing config..."
cp -n "$REPO_DIR/config/config.toml" "$USER_CONFIG_DIR/config.toml"
cp -n "$REPO_DIR/config/theme.toml" "$USER_CONFIG_DIR/theme.toml"

echo "[GSM] Installing systemd units..."
mkdir -p "$USER_SYSTEMD_DIR"
sed "s|%h/gsm|$REPO_DIR|g" "$REPO_DIR/systemd/gsm.service" > "$USER_SYSTEMD_DIR/gsm.service"
cp "$REPO_DIR/systemd/gsm.timer" "$USER_SYSTEMD_DIR/gsm.timer"
systemctl --user daemon-reload
systemctl --user enable --now gsm.timer

echo "[GSM] Installing autostart entry..."
mkdir -p "$USER_AUTOSTART_DIR"
cp "$REPO_DIR/desktop/gsm.desktop" "$USER_AUTOSTART_DIR/gsm.desktop"

chmod +x "$REPO_DIR/src/core/config.sh"
chmod +x "$REPO_DIR/src/gsm_cli.sh"
chmod +x "$REPO_DIR/src/gsm_tui.sh"
chmod +x "$REPO_DIR/src/gsm_gui.py"
chmod +x "$REPO_DIR/scripts/uninstall.sh"

echo "[GSM] Setup complete."
