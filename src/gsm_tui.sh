#!/usr/bin/env bash

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="$BASE_DIR/gsm_cli.sh"
CONFIG_FILE="$HOME/.config/gsm/config.toml"

get_config() {
    grep -E "^$1[[:space:]]*=" "$CONFIG_FILE" | head -n1 | cut -d'=' -f2- | sed 's/^ *//' | sed 's/"//g'
}

show_settings() {
    clear
    echo "=============================="
    echo " GSM Settings"
    echo "=============================="
    echo "Remote: $(get_config remote)"
    echo "Max backups per game: $(get_config max_backups_per_game)"
    echo "Schedule: $(get_config schedule)"
    echo
    echo "1. Change remote"
    echo "2. Change max backups per game"
    echo "3. Change schedule"
    echo "4. Back"
    echo
    read -r -p "Select an option: " opt

    case "$opt" in
        1)
            read -r -p "New remote: " value
            "$CLI" update-remote "$value"
            ;;
        2)
            read -r -p "New max backups per game: " value
            "$CLI" update-max-backups "$value"
            ;;
        3)
            read -r -p "New schedule (example: *-*-* 22:00): " value
            "$CLI" update-schedule "$value"
            ;;
        4)
            return
            ;;
        *)
            echo "Invalid option"
            ;;
    esac

    echo
    read -r -p "Press Enter to continue..."
}

while true; do
    clear
    cat <<'MENU'
╔══════════════════════════════════╗
║               GSM                ║
║      Game Save Manager - TUI     ║
╠══════════════════════════════════╣
║ 1. Automatic Backup              ║
║ 2. Manual Backup                 ║
║ 3. Restore Latest                ║
║ 4. Sync From Cloud               ║
║ 5. Refresh History               ║
║ 6. Settings                      ║
║ 7. Exit                          ║
╚══════════════════════════════════╝
MENU

    printf "Select an option: "
    read -r opt

    case "$opt" in
        1)
            "$CLI" backup
            ;;
        2)
            printf "Save path: "
            read -r save_path
            printf "Game name: "
            read -r game_name
            "$CLI" manual-backup "$save_path" "$game_name"
            ;;
        3)
            "$CLI" restore
            ;;
        4)
            "$CLI" sync
            ;;
        5)
            "$CLI" history
            ;;
        6)
            show_settings
            ;;
        7)
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac

    echo
    read -r -p "Press Enter to continue..."
done
