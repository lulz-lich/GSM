# GSM Architecture

GSM (Game Save Manager) is a cross-platform system for backing up, storing, syncing, and restoring game save data safely across Linux and Windows.

The design is intentionally simple and avoids destructive operations.

---

## Core Idea

GSM does NOT treat the cloud as a mirror of your saves.

Instead, it treats the cloud as a **versioned backup library**.

This means:

- Every backup creates a new version
- Old backups are preserved (within limits)
- Nothing is overwritten silently
- Restore is always explicit

---

## High-Level Flow

```text
Game Save → Detection → Archive → Cloud Storage
                                 ↓
                          Local Backup Library
                                 ↓
                              Restore
