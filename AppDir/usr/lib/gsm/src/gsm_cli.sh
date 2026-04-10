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

cleanup_restore() {
    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"
}

prune_local_game_backups() {
    local game_name="$1"

    mapfile -t files < <(
        find "$BACKUP_DIR" -maxdepth 1 -type f -name "${game_name}_*.tar.gz" | sort
    )

    local count="${#files[@]}"
    if [ "$count" -le "$MAX_BACKUPS_PER_GAME" ]; then
        return 0
    fi

    local remove_count=$((count - MAX_BACKUPS_PER_GAME))
    for ((i=0; i<remove_count; i++)); do
        local old_file="${files[$i]}"
        log "Removing old local backup: $(basename "$old_file")"
        rm -f "$old_file" "${old_file}.sha256"
    done
}

prune_remote_game_backups() {
    local game_name="$1"

    mapfile -t remote_files < <(
        rclone lsf "$REMOTE/$game_name" --files-only 2>/dev/null | grep '\.tar\.gz$' | sort || true
    )

    local count="${#remote_files[@]}"
    if [ "$count" -le "$MAX_BACKUPS_PER_GAME" ]; then
        return 0
    fi

    local remove_count=$((count - MAX_BACKUPS_PER_GAME))
    for ((i=0; i<remove_count; i++)); do
        local old_file="${remote_files[$i]}"
        log "Removing old remote backup: $old_file"
        rclone deletefile "$REMOTE/$game_name/$old_file" || true
        rclone deletefile "$REMOTE/$game_name/${old_file}.sha256" || true
    done
}

create_archive_for_game() {
    local game_name="$1"
    local timestamp="$2"

    local archive_file="$BACKUP_DIR/${game_name}_${timestamp}.tar.gz"

    tar -czf "$archive_file" -C "$TEMP_DIR" "$game_name"
    sha256sum "$archive_file" > "${archive_file}.sha256"

    log "Uploading $game_name..."
    rclone copy "$archive_file" "$REMOTE/$game_name/" -P
    if [ -f "${archive_file}.sha256" ]; then
        rclone copy "${archive_file}.sha256" "$REMOTE/$game_name/" -P
    fi

    prune_local_game_backups "$game_name"
    prune_remote_game_backups "$game_name"
}

backup_auto() {
    cleanup_temp
    log "Starting automatic backup with Ludusavi"
    ludusavi backup --path "$TEMP_DIR" --force

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

sync_library() {
    log "Syncing backup library from cloud..."
    mkdir -p "$BACKUP_DIR"
    rclone copy "$REMOTE" "$BACKUP_DIR" -P
    log "Backup library sync completed"
}

restore_latest() {
    sync_library

    local latest_archive
    latest_archive="$(find "$BACKUP_DIR" -type f -name '*.tar.gz' | sort | tail -n1)"

    if [ -z "$latest_archive" ]; then
        log "No local archives found after sync"
        exit 1
    fi

    cleanup_restore
    tar -xzf "$latest_archive" -C "$RESTORE_DIR"

    log "Restoring from latest archive: $latest_archive"
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore latest completed"
}

restore_all() {
    sync_library
    cleanup_restore

    shopt -s nullglob
    local found=0
    for archive in "$BACKUP_DIR"/*.tar.gz; do
        found=1
        tar -xzf "$archive" -C "$RESTORE_DIR"
    done
    shopt -u nullglob

    if [ "$found" -eq 0 ]; then
        log "No local archives found to restore"
        exit 1
    fi

    log "Restoring all extracted backups..."
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore all completed"
}

restore_game_latest() {
    local game_name="${1:-}"

    if [ -z "$game_name" ]; then
        log "restore-game requires a game name"
        exit 1
    fi

    sync_library

    local latest_archive
    latest_archive="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name "${game_name}_*.tar.gz" | sort | tail -n1)"

    if [ -z "$latest_archive" ]; then
        log "No backup found for game: $game_name"
        exit 1
    fi

    cleanup_restore
    tar -xzf "$latest_archive" -C "$RESTORE_DIR"

    log "Restoring latest backup for $game_name from $latest_archive"
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore game completed"
}

refresh_history() {
    find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.tar.gz' | sort
}

restore_file() {
    local archive_file="${1:-}"

    if [ -z "$archive_file" ] || [ ! -f "$archive_file" ]; then
        log "Restore requires a valid local archive path"
        exit 1
    fi

    cleanup_restore
    tar -xzf "$archive_file" -C "$RESTORE_DIR"

    log "Restoring from $archive_file"
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore completed"
}

usage() {
    cat <<USAGE
GSM CLI

Usage:
  ./src/gsm_cli.sh backup
  ./src/gsm_cli.sh manual-backup "/path/to/save" "Game Name"
  ./src/gsm_cli.sh sync
  ./src/gsm_cli.sh restore
  ./src/gsm_cli.sh restore-all
  ./src/gsm_cli.sh restore-game "Game Name"
  ./src/gsm_cli.sh restore-file "/path/to/archive.tar.gz"
  ./src/gsm_cli.sh history
USAGE
}

cmd="${1:-}"

case "$cmd" in
    backup)
        check_running_games
        backup_auto
        ;;
    manual-backup)
        check_running_games
        backup_manual "${2:-}" "${3:-}"
        ;;
    sync)
        sync_library
        ;;
    restore)
        restore_latest
        ;;
    restore-all)
        restore_all
        ;;
    restore-game)
        restore_game_latest "${2:-}"
        ;;
    restore-file)
        restore_file "${2:-}"
        ;;
    history)
        refresh_history
        ;;
    *)
        usage
        exit 1
        ;;
esac
