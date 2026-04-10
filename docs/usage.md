# GSM Usage Guide

GSM (Game Save Manager) lets you backup, sync, and restore game saves across Linux and Windows.

---

## Core Idea (read this or regret later)

GSM separates everything into 3 actions:

- **Backup** → creates a new version of your save
- **Sync** → downloads backups from the cloud
- **Restore** → overwrites your current save with a backup

If you mix these up, you will lose progress.

---

## Safe Workflow

Always follow this when restoring:

```text
1. Backup current save
2. Sync (if using another machine)
3. Restore desired version
