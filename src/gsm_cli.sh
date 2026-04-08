#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$BASE_DIR/core/config.sh"

USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
TIMER_FILE="$USER_SYSTEMD_DIR/gsm.timer"
SERVICE_FILE="$USER_SYSTEMD_DIR/gsm.service"

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
        rclone lsf "$REMOTE/$game_name" --files-only | grep '\.tar\.gz$' | sort
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
    rclone copy "$archive_file" "$REMOTE/$game_name/"
    rclone copy "${archive_file}.sha256" "$REMOTE/$game_name/"

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
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore completed"
}

restore_file() {
    local archive_file="${1:-}"

    if [ -z "$archive_file" ] || [ ! -f "$archive_file" ]; then
        log "Restore requires a valid local archive path"
        exit 1
    fi

    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"

    tar -xzf "$archive_file" -C "$RESTORE_DIR"
    log "Restoring from $archive_file"
    ludusavi restore --path "$RESTORE_DIR" --force
    log "Restore completed"
}

sync_local_from_cloud() {
    log "Syncing cloud backups to local backup directory"
    rclone sync "$REMOTE" "$BACKUP_DIR"
    log "Sync completed"
}

refresh_history() {
    find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.tar.gz' | sort
}

write_timer() {
    mkdir -p "$USER_SYSTEMD_DIR"

    cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=GSM backup service

[Service]
Type=oneshot
WorkingDirectory=$HOME/gsm
ExecStart=$HOME/gsm/src/gsm_cli.sh backup
SERVICE

    cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Run GSM backup on schedule

[Timer]
OnCalendar=$SCHEDULE
Persistent=true

[Install]
WantedBy=timers.target
TIMER

    systemctl --user daemon-reload
    systemctl --user enable --now gsm.timer >/dev/null 2>&1 || true
}

update_schedule() {
    local new_schedule="${1:-}"
    if [ -z "$new_schedule" ]; then
        log "update-schedule requires a value"
        exit 1
    fi

    set_config "schedule" "$new_schedule" "$CONFIG_FILE"
    SCHEDULE="$new_schedule"
    write_timer
    log "Schedule updated to: $new_schedule"
}

update_remote() {
    local new_remote="${1:-}"
    if [ -z "$new_remote" ]; then
        log "update-remote requires a value"
        exit 1
    fi

    set_config "remote" "$new_remote" "$CONFIG_FILE"
    log "Remote updated to: $new_remote"
}

update_max_backups() {
    local new_max="${1:-}"
    if ! [[ "$new_max" =~ ^[0-9]+$ ]]; then
        log "update-max-backups requires a positive integer"
        exit 1
    fi

    set_config_raw "max_backups_per_game" "$new_max" "$CONFIG_FILE"
    log "Max backups per game updated to: $new_max"
}

usage() {
    cat <<USAGE
GSM CLI

Usage:
  ./src/gsm_cli.sh backup
  ./src/gsm_cli.sh restore
  ./src/gsm_cli.sh restore-file "/path/to/archive.tar.gz"
  ./src/gsm_cli.sh sync
  ./src/gsm_cli.sh history
  ./src/gsm_cli.sh manual-backup "/path/to/save" "Game Name"
  ./src/gsm_cli.sh update-schedule "*-*-* 22:00"
  ./src/gsm_cli.sh update-remote "onedrive:/game-backups"
  ./src/gsm_cli.sh update-max-backups 7
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
    restore-file)
        restore_file "${2:-}"
        ;;
    sync)
        sync_local_from_cloud
        ;;
    history)
        refresh_history
        ;;
    manual-backup)
        check_running_games
        backup_manual "${2:-}" "${3:-}"
        ;;
    update-schedule)
        update_schedule "${2:-}"
        ;;
    update-remote)
        update_remote "${2:-}"
        ;;
    update-max-backups)
        update_max_backups "${2:-}"
        ;;
    *)
        usage
        exit 1
        ;;
esac
