#!/usr/bin/env bash
set -euo pipefail

USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
USER_AUTOSTART_DIR="$HOME/.config/autostart"

systemctl --user disable --now gsm.timer || true
rm -f "$USER_SYSTEMD_DIR/gsm.service"
rm -f "$USER_SYSTEMD_DIR/gsm.timer"
systemctl --user daemon-reload
rm -f "$USER_AUTOSTART_DIR/gsm.desktop"

echo "[GSM] Uninstalled system integration."
echo "[GSM] User config in ~/.config/gsm was kept."
