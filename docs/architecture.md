# GSM Architecture

GSM is split into three user-facing entry points:

- `gsm_cli.sh` for scripting and automation
- `gsm_tui.sh` for terminal interaction
- `gsm_gui.py` for GTK desktop interaction

## Core flow

1. load user config
2. optionally check for game-like running processes
3. use Ludusavi to detect and collect save data
4. allow manual fallback if enabled or requested
5. create per-game tar.gz archives
6. generate SHA256 files
7. upload archives to the configured Rclone remote
8. clean old local backups according to retention policy

## Remote organization

Each game gets its own folder on the cloud remote:

```text
remote_root/GameName/GameName_timestamp.tar.gz
```
