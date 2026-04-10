# GSM Architecture

GSM (Game Save Manager) is a cross-platform tool designed to safely manage game save backups across Linux and Windows.

The system is built around a simple but robust model:

- Save detection (Ludusavi)
- Versioned backup creation
- Cloud storage (Rclone)
- Local backup library
- Explicit restore operations

---

## Core Design Principles

1. No destructive sync operations
2. Backups are immutable versions
3. Cloud is treated as a backup library, not a mirror
4. Restore is always explicit
5. Cross-platform compatibility is preserved

---

## System Components

### 1. Detection Layer

Uses Ludusavi to detect game save locations.

Output:
```text
Temporary directory containing per-game save folders
