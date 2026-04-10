#!/usr/bin/env bash

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="$BASE_DIR/gsm_cli.sh"

while true; do
    clear
    cat <<'MENU'
╔══════════════════════════════════╗
║               GSM                ║
║      Game Save Manager - TUI     ║
╠══════════════════════════════════╣
║ 1. Automatic Backup              ║
║ 2. Manual Backup                 ║
║ 3. Sync Backup Library           ║
║ 4. Restore Latest                ║
║ 5. Restore All                   ║
║ 6. Restore Specific Game         ║
║ 7. Refresh History               ║
║ 8. Exit                          ║
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
            "$CLI" sync
            ;;
        4)
            "$CLI" restore
            ;;
        5)
            "$CLI" restore-all
            ;;
        6)
            printf "Game name: "
            read -r game_name
            "$CLI" restore-game "$game_name"
            ;;
        7)
            "$CLI" history
            ;;
        8)
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac

    echo
    read -r -p "Press Enter to continue..."
done
