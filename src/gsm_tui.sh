#!/usr/bin/env bash

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

while true; do
    clear
    cat <<'MENU'
╔══════════════════════════════╗
║             GSM              ║
║   Game Save Manager - TUI    ║
╠══════════════════════════════╣
║ 1. Automatic backup          ║
║ 2. Manual backup             ║
║ 3. Restore latest            ║
║ 4. Sync from cloud           ║
║ 5. Exit                      ║
╚══════════════════════════════╝
MENU

    printf "Select an option: "
    read -r opt

    case "$opt" in
        1)
            "$BASE_DIR/gsm_cli.sh" backup
            ;;
        2)
            printf "Save path: "
            read -r save_path
            printf "Game name: "
            read -r game_name
            "$BASE_DIR/gsm_cli.sh" manual-backup "$save_path" "$game_name"
            ;;
        3)
            "$BASE_DIR/gsm_cli.sh" restore
            ;;
        4)
            "$BASE_DIR/gsm_cli.sh" sync
            ;;
        5)
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac

    echo
    read -r -p "Press Enter to continue..."
done
