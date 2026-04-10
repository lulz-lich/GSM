#!/usr/bin/env bash

CONFIG_FILE="$HOME/.config/gsm/config.toml"

read_config() {
    local key="$1"
    local file="$2"
    grep -E "^${key}[[:space:]]*=" "$file" | head -n1 | cut -d'=' -f2- | sed 's/^ *//' | sed 's/"//g'
}

expand_path() {
    local path="$1"
    echo "${path/#\~/$HOME}"
}

if [ ! -f "$CONFIG_FILE" ]; then
    echo "GSM config not found: $CONFIG_FILE"
    exit 1
fi

BACKUP_DIR="$(expand_path "$(read_config backup_dir "$CONFIG_FILE")")"
TEMP_DIR="$(expand_path "$(read_config temp_dir "$CONFIG_FILE")")"
RESTORE_DIR="$(expand_path "$(read_config restore_dir "$CONFIG_FILE")")"
LOG_FILE="$(expand_path "$(read_config log_file "$CONFIG_FILE")")"
REMOTE="$(read_config remote "$CONFIG_FILE")"
RETENTION_DAYS="$(read_config retention_days "$CONFIG_FILE")"
MAX_BACKUPS_PER_GAME="$(read_config max_backups_per_game "$CONFIG_FILE")"
CHECK_RUNNING_PROCESSES="$(read_config check_running_processes "$CONFIG_FILE")"
RUNNING_PROCESS_PATTERNS="$(read_config running_process_patterns "$CONFIG_FILE")"

RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_BACKUPS_PER_GAME="${MAX_BACKUPS_PER_GAME:-7}"
CHECK_RUNNING_PROCESSES="${CHECK_RUNNING_PROCESSES:-true}"
RUNNING_PROCESS_PATTERNS="${RUNNING_PROCESS_PATTERNS:-steam|wine|gamescope|\\.exe}"

mkdir -p "$BACKUP_DIR"
mkdir -p "$TEMP_DIR"
mkdir -p "$RESTORE_DIR"
mkdir -p "$(dirname "$LOG_FILE")"
