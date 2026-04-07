#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$BASE_DIR/core/config.sh"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_running_games() {
    if [ "$CHECK_RUNNING_PROCESSES" != "true" ]; then
        return 0
    fi

    if ps aux | grep -E "$RUNNING_PROCESS_PATTERNS" | grep -v grep >/dev/null 2>&1; then
        log "Detected possible running game-related process. Aborting."
        return 1
    fi
    return 0
}

cleanup_temp() {
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
}

create_archive_for_game() {
    local game_name="$1"
    local timestamp="$2"

    local archive_file="$BACKUP_DIR/${game_name}_${timestamp}.tar.gz"
    tar -czf "$archive_file" -C "$TEMP_DIR" "$game_name"
    sha256sum "$archive_file" > "${archive_file}.sha256"

    rclone copy "$archive_file" "$REMOTE/$game_name/"
    rclone copy "${archive_file}.sha256" "$REMOTE/$game_name/"
}

backup_auto() {
    cleanup_temp
    log "Starting automatic backup with Ludusavi"
    ludusavi backup --path "$TEMP_DIR"

    if ! find "$TEMP_DIR" -mindepth 1 -maxdepth 1 | grep -q .; then
        log "No saves detected by Ludusavi"
        return 1
    fi

    local timestamp
    timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"

    for dir in "$TEMP_DIR"/*; do
        [ -d "$dir" ] || continue
        local game_name
        game_name="$(basename "$dir")"
        log "Archiving and uploading $game_name"
        create_archive_for_game "$game_name" "$timestamp"
    done

    find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete
    log "Automatic backup completed"
}

backup_manual() {
    local save_path="${1:-}"
    local game_name="${2:-}"

    if [ -z "$save_path" ] || [ -z "$game_name" ]; then
        log "Manual backup requires: save_path and game_name"
        exit 1
    fi

    cleanup_temp
    mkdir -p "$TEMP_DIR/$game_name"
    cp -a "$save_path"/. "$TEMP_DIR/$game_name"/

    local timestamp
    timestamp="$(date '+%Y-%m-%d_%H-%M-%S')"

    log "Archiving and uploading manual save for $game_name"
    create_archive_for_game "$game_name" "$timestamp"

    find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete
    log "Manual backup completed"
}

restore_latest() {
    log "Syncing cloud backups to local directory"
    rclone sync "$REMOTE" "$BACKUP_DIR"

    local latest_archive
    latest_archive="$(find "$BACKUP_DIR" -type f -name '*.tar.gz' | sort | tail -n1)"

    if [ -z "$latest_archive" ]; then
        log "No local archives found after sync"
        exit 1
    fi

    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"

    tar -xzf "$latest_archive" -C "$RESTORE_DIR"
    log "Restoring from $latest_archive"
    ludusavi restore --path "$RESTORE_DIR"
    log "Restore completed"
}

sync_local_from_cloud() {
    log "Syncing cloud to local backup directory"
    rclone sync "$REMOTE" "$BACKUP_DIR"
    log "Sync completed"
}

usage() {
    cat <<USAGE
GSM CLI

Usage:
  ./src/gsm_cli.sh backup
  ./src/gsm_cli.sh restore
  ./src/gsm_cli.sh sync
  ./src/gsm_cli.sh manual-backup "/path/to/save" "Game Name"
USAGE
}

cmd="${1:-}"

case "$cmd" in
    backup)
        check_running_games
        backup_auto
        ;;
    restore)
        restore_latest
        ;;
    sync)
        sync_local_from_cloud
        ;;
    manual-backup)
        check_running_games
        backup_manual "${2:-}" "${3:-}"
        ;;
    *)
        usage
        exit 1
        ;;
esac
