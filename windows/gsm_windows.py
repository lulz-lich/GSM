#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import shutil
import tarfile
import hashlib
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "GSM")
RCLONE_CONFIG = os.path.join(APPDATA, "rclone", "rclone.conf")
LOCAL_BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "GSM", "Backups")
RESTORE_DIR = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "gsm_restore")
TEMP_DIR = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "gsm_tmp")
DEFAULT_REMOTE_NAME = ""
DEFAULT_REMOTE_FOLDER = "game-backups"

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, name)

def rclone():
    return resource_path("rclone.exe")

def ludusavi():
    return resource_path("ludusavi.exe")

def cloud_ready():
    return os.path.isfile(RCLONE_CONFIG)

def run_console(cmd):
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)

def build_remote_path(remote_name, folder):
    remote_name = remote_name.strip().rstrip(":")
    folder = folder.strip().lstrip("/")
    if not remote_name:
        return ""
    if not folder:
        return f"{remote_name}:"
    return f"{remote_name}:/{folder}"

def split_remote_path(remote_path):
    remote_path = remote_path.strip()
    if not remote_path or ":" not in remote_path:
        return "", DEFAULT_REMOTE_FOLDER
    remote_name, rest = remote_path.split(":", 1)
    folder = rest.strip().lstrip("/") or DEFAULT_REMOTE_FOLDER
    return remote_name.strip(), folder

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GSM")
        self.geometry("1160x780")
        self.configure(bg="#1e1e2e")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._apply_theme()

        self.status = tk.StringVar(value="Idle")
        self.remote_name_var = tk.StringVar()
        self.remote_folder_var = tk.StringVar(value=DEFAULT_REMOTE_FOLDER)
        self.max_backups_var = tk.StringVar(value="7")

        self._build_ui()
        self.load_settings_into_ui()
        self.refresh_remotes()
        self.refresh_cloud_status()
        self.refresh_history()

    def _apply_theme(self):
        self.style.configure(".", background="#1e1e2e", foreground="#cdd6f4", fieldbackground="#11111b")
        self.style.configure("TFrame", background="#1e1e2e")
        self.style.configure("Card.TFrame", background="#181825")
        self.style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4")
        self.style.configure("Card.TLabel", background="#181825", foreground="#cdd6f4")
        self.style.configure("Title.TLabel", background="#1e1e2e", foreground="#f5e0dc", font=("Segoe UI", 22, "bold"))
        self.style.configure("Sub.TLabel", background="#1e1e2e", foreground="#a6adc8", font=("Segoe UI", 10))
        self.style.configure("TButton", background="#313244", foreground="#cdd6f4", padding=8)
        self.style.map("TButton", background=[("active", "#45475a")])
        self.style.configure("Primary.TButton", background="#89b4fa", foreground="#11111b", padding=8)
        self.style.map("Primary.TButton", background=[("active", "#74c7ec")])
        self.style.configure("TCombobox", fieldbackground="#11111b", background="#313244", foreground="#cdd6f4")

    def _build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=18, pady=18)

        ttk.Label(root, text="GSM", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="Game Save Manager for Windows", style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        top = ttk.Frame(root, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 12))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Status:", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=10)
        ttk.Label(top, textvariable=self.status, style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=12, pady=10)

        self.cloud_state_label = ttk.Label(top, text="", style="Card.TLabel")
        self.cloud_state_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(0, 12))

        ttk.Button(btns, text="Configure Cloud", command=self.configure_cloud, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Refresh Cloud Status", command=self.refresh_cloud_status).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Automatic Backup", command=self.automatic_backup, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Manual Backup", command=self.manual_backup).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Sync Backup Library", command=self.sync_library).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Restore Latest", command=self.restore_latest).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Restore All", command=self.restore_all).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Restore Selected Game", command=self.restore_selected_game).pack(side="left", padx=(0, 8))

        settings = ttk.Frame(root, style="Card.TFrame")
        settings.pack(fill="x", pady=(0, 12))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Cloud Remote", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=8)

        remote_row = ttk.Frame(settings, style="Card.TFrame")
        remote_row.grid(row=0, column=1, sticky="ew", padx=12, pady=8)
        remote_row.columnconfigure(0, weight=1)

        self.remote_combo = ttk.Combobox(remote_row, textvariable=self.remote_name_var, state="readonly")
        self.remote_combo.grid(row=0, column=0, sticky="ew")

        ttk.Button(remote_row, text="Reload", command=self.refresh_remotes).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(settings, text="Cloud Folder", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=12, pady=8)
        ttk.Entry(settings, textvariable=self.remote_folder_var).grid(row=1, column=1, sticky="ew", padx=12, pady=8)

        ttk.Label(settings, text="Max Backups per Game", style="Card.TLabel").grid(row=2, column=0, sticky="w", padx=12, pady=8)
        ttk.Entry(settings, textvariable=self.max_backups_var).grid(row=2, column=1, sticky="ew", padx=12, pady=8)

        self.remote_preview_label = ttk.Label(settings, text="", style="Card.TLabel")
        self.remote_preview_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

        ttk.Button(settings, text="Save Settings", command=self.save_settings).grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))

        self.remote_name_var.trace_add("write", lambda *_: self.update_remote_preview())
        self.remote_folder_var.trace_add("write", lambda *_: self.update_remote_preview())

        middle = ttk.Frame(root)
        middle.pack(fill="both", expand=True, pady=(0, 12))

        left = ttk.Frame(middle, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = ttk.Frame(middle, style="Card.TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        ttk.Label(left, text="Detected Games", style="Card.TLabel").pack(anchor="w", padx=12, pady=(12, 6))
        self.detected_list = tk.Listbox(left, bg="#11111b", fg="#cdd6f4", relief="flat", height=10)
        self.detected_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ttk.Label(right, text="Local Backup History", style="Card.TLabel").pack(anchor="w", padx=12, pady=(12, 6))
        self.history_list = tk.Listbox(right, bg="#11111b", fg="#cdd6f4", relief="flat", height=10)
        self.history_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        logs_card = ttk.Frame(root, style="Card.TFrame")
        logs_card.pack(fill="both", expand=True)

        ttk.Label(logs_card, text="Logs", style="Card.TLabel").pack(anchor="w", padx=12, pady=(12, 6))

        self.log_text = tk.Text(
            logs_card,
            bg="#11111b",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
            height=14
        )
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text.configure(state="disabled")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_status(self, text):
        self.status.set(text)
        self.log(text)

    def update_remote_preview(self):
        preview = build_remote_path(self.remote_name_var.get(), self.remote_folder_var.get())
        if preview:
            self.remote_preview_label.config(text=f"Remote path: {preview}")
        else:
            self.remote_preview_label.config(text="Remote path: not configured")

    def get_remotes(self):
        try:
            out = subprocess.check_output([rclone(), "listremotes"], text=True)
            return [x.strip().replace(":", "") for x in out.splitlines() if x.strip()]
        except Exception:
            return []

    def refresh_remotes(self):
        remotes = self.get_remotes()
        self.remote_combo["values"] = remotes

        current = self.remote_name_var.get().strip()
        if current and current in remotes:
            self.remote_combo.set(current)
        elif remotes:
            self.remote_combo.set(remotes[0])
            self.remote_name_var.set(remotes[0])
        else:
            self.remote_combo.set("")
            self.remote_name_var.set("")

        self.update_remote_preview()

    def refresh_cloud_status(self):
        self.refresh_remotes()
        remotes = self.get_remotes()

        if cloud_ready() and remotes:
            self.cloud_state_label.config(text=f"Cloud configured. Available remotes: {', '.join(remotes)}")
            self.set_status("Cloud is configured")
        elif cloud_ready():
            self.cloud_state_label.config(text="rclone config exists, but no remotes were found.")
            self.set_status("Cloud config found, but no remotes detected")
        else:
            self.cloud_state_label.config(text="Cloud is not configured yet. Click 'Configure Cloud'.")
            self.set_status("Cloud is not configured")

    def configure_cloud(self):
        if not os.path.exists(rclone()):
            messagebox.showerror("Error", "Bundled rclone.exe not found.")
            return

        messagebox.showinfo(
            "Configure Cloud",
            "A console window will open with rclone setup.\n\nCreate any remote name you want.\nThen return here and click 'Refresh Cloud Status'."
        )
        run_console([rclone(), "config"])

    def save_settings(self):
        remote_name = self.remote_name_var.get().strip()
        remote_folder = self.remote_folder_var.get().strip()
        max_backups = self.max_backups_var.get().strip()

        if not remote_name:
            messagebox.showerror("Error", "Please select a cloud remote.")
            return

        if not remote_folder:
            messagebox.showerror("Error", "Cloud folder cannot be empty.")
            return

        if not max_backups.isdigit():
            messagebox.showerror("Error", "Max backups per game must be a number.")
            return

        remote_path = build_remote_path(remote_name, remote_folder)
        cfg_path = os.path.join(CONFIG_DIR, "settings.ini")

        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(f"remote={remote_path}\n")
            f.write(f"max_backups_per_game={max_backups}\n")

        self.update_remote_preview()
        self.set_status("Settings saved")

    def load_settings(self):
        cfg_path = os.path.join(CONFIG_DIR, "settings.ini")
        if not os.path.isfile(cfg_path):
            return build_remote_path(DEFAULT_REMOTE_NAME, DEFAULT_REMOTE_FOLDER), 7

        remote = build_remote_path(DEFAULT_REMOTE_NAME, DEFAULT_REMOTE_FOLDER)
        max_backups = 7

        with open(cfg_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("remote="):
                    remote = line.split("=", 1)[1]
                elif line.startswith("max_backups_per_game="):
                    value = line.split("=", 1)[1]
                    if value.isdigit():
                        max_backups = int(value)

        return remote, max_backups

    def load_settings_into_ui(self):
        remote_path, max_backups = self.load_settings()
        remote_name, remote_folder = split_remote_path(remote_path)

        self.remote_name_var.set(remote_name)
        self.remote_folder_var.set(remote_folder)
        self.max_backups_var.set(str(max_backups))
        self.update_remote_preview()

    def get_remote_path(self):
        return build_remote_path(self.remote_name_var.get(), self.remote_folder_var.get())

    def run_command_and_log(self, command):
        self.log("$ " + " ".join(command))
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in proc.stdout:
            self.log(line.rstrip())

        return proc.wait()

    def refresh_history(self):
        self.history_list.delete(0, "end")
        if not os.path.isdir(LOCAL_BACKUP_DIR):
            return
        for name in sorted(os.listdir(LOCAL_BACKUP_DIR), reverse=True):
            if name.endswith(".tar.gz"):
                self.history_list.insert("end", name)

    def add_detected_games(self, games):
        self.detected_list.delete(0, "end")
        for game in games:
            self.detected_list.insert("end", game)

    def prune_local_game_backups(self, game_name, max_backups):
        files = sorted(
            [
                os.path.join(LOCAL_BACKUP_DIR, f)
                for f in os.listdir(LOCAL_BACKUP_DIR)
                if f.startswith(f"{game_name}_") and f.endswith(".tar.gz")
            ]
        )

        if len(files) <= max_backups:
            return

        for old in files[:-max_backups]:
            sha = old + ".sha256"
            self.log(f"Removing old local backup: {os.path.basename(old)}")
            if os.path.exists(old):
                os.remove(old)
            if os.path.exists(sha):
                os.remove(sha)

    def prune_remote_game_backups(self, remote_base, game_name, max_backups):
        try:
            out = subprocess.check_output(
                [rclone(), "lsf", f"{remote_base}/{game_name}", "--files-only"],
                text=True,
                stderr=subprocess.STDOUT
            )
            files = sorted([x.strip() for x in out.splitlines() if x.strip().endswith(".tar.gz")])
        except subprocess.CalledProcessError:
            files = []

        if len(files) <= max_backups:
            return

        for old in files[:-max_backups]:
            self.log(f"Removing old remote backup: {old}")
            subprocess.call([rclone(), "deletefile", f"{remote_base}/{game_name}/{old}"])
            subprocess.call([rclone(), "deletefile", f"{remote_base}/{game_name}/{old}.sha256"])

    def create_archive(self, source_dir, game_name):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_name = f"{game_name}_{ts}.tar.gz"
        archive_path = os.path.join(LOCAL_BACKUP_DIR, archive_name)

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_dir, arcname=game_name)

        digest = sha256_file(archive_path)
        with open(archive_path + ".sha256", "w", encoding="utf-8") as f:
            f.write(f"{digest}  {archive_name}\n")

        return archive_path

    def automatic_backup(self):
        if not cloud_ready():
            messagebox.showwarning("Error", "Cloud not configured")
            return
        if not self.remote_name_var.get().strip():
            messagebox.showwarning("Error", "No remote selected")
            return
        threading.Thread(target=self._automatic_backup_worker, daemon=True).start()

    def _automatic_backup_worker(self):
        self.set_status("Detecting saves...")

        if os.path.isdir(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
        os.makedirs(TEMP_DIR, exist_ok=True)

        detect_code = self.run_command_and_log([ludusavi(), "backup", "--path", TEMP_DIR, "--force"])
        if detect_code != 0:
            self.set_status("Detection failed")
            return

        games = [d for d in os.listdir(TEMP_DIR) if os.path.isdir(os.path.join(TEMP_DIR, d))]
        self.add_detected_games(games)

        if not games:
            self.set_status("No saves detected")
            return

        remote_base = self.get_remote_path()
        max_backups = int(self.max_backups_var.get())

        for game in games:
            game_dir = os.path.join(TEMP_DIR, game)
            self.set_status(f"Creating archive for {game}...")
            archive_path = self.create_archive(game_dir, game)

            self.set_status(f"Uploading {game}...")
            code = self.run_command_and_log([rclone(), "copy", archive_path, f"{remote_base}/{game}"])
            if code != 0:
                self.set_status(f"Upload failed for {game}")
                return

            sha_path = archive_path + ".sha256"
            if os.path.exists(sha_path):
                self.run_command_and_log([rclone(), "copy", sha_path, f"{remote_base}/{game}"])

            self.prune_local_game_backups(game, max_backups)
            self.prune_remote_game_backups(remote_base, game, max_backups)

        self.refresh_history()
        self.set_status("Automatic backup completed")

    def manual_backup(self):
        if not cloud_ready():
            messagebox.showwarning("Error", "Cloud not configured")
            return
        if not self.remote_name_var.get().strip():
            messagebox.showwarning("Error", "No remote selected")
            return

        folder = filedialog.askdirectory(title="Select save folder")
        if not folder:
            return

        game_name = simpledialog.askstring("Game Name", "Enter game name")
        if not game_name:
            return

        threading.Thread(target=self._manual_backup_worker, args=(folder, game_name), daemon=True).start()

    def _manual_backup_worker(self, folder, game_name):
        remote_base = self.get_remote_path()
        max_backups = int(self.max_backups_var.get())

        self.set_status(f"Creating archive for {game_name}...")
        archive_path = self.create_archive(folder, game_name)

        self.set_status(f"Uploading {game_name}...")
        code = self.run_command_and_log([rclone(), "copy", archive_path, f"{remote_base}/{game_name}"])
        if code != 0:
            self.set_status("Manual backup failed")
            return

        sha_path = archive_path + ".sha256"
        if os.path.exists(sha_path):
            self.run_command_and_log([rclone(), "copy", sha_path, f"{remote_base}/{game_name}"])

        self.prune_local_game_backups(game_name, max_backups)
        self.prune_remote_game_backups(remote_base, game_name, max_backups)

        self.refresh_history()
        self.set_status("Manual backup completed")

    def sync_library(self):
        if not cloud_ready():
            messagebox.showwarning("Error", "Cloud not configured")
            return
        if not self.remote_name_var.get().strip():
            messagebox.showwarning("Error", "No remote selected")
            return
        threading.Thread(target=self._sync_library_worker, daemon=True).start()

    def _sync_library_worker(self):
        remote = self.get_remote_path()
        self.set_status("Syncing backup library from cloud...")
        code = self.run_command_and_log([rclone(), "copy", remote, LOCAL_BACKUP_DIR])
        if code != 0:
            self.set_status("Sync failed")
            return
        self.refresh_history()
        self.set_status("Sync completed")

    def restore_latest(self):
        threading.Thread(target=self._restore_latest_worker, daemon=True).start()

    def _restore_latest_worker(self):
        self._sync_library_worker()

        archives = sorted(
            [os.path.join(LOCAL_BACKUP_DIR, f) for f in os.listdir(LOCAL_BACKUP_DIR) if f.endswith(".tar.gz")]
        )
        if not archives:
            self.set_status("No local archives found")
            return

        latest = archives[-1]

        if os.path.isdir(RESTORE_DIR):
            shutil.rmtree(RESTORE_DIR, ignore_errors=True)
        os.makedirs(RESTORE_DIR, exist_ok=True)

        self.set_status(f"Extracting latest archive: {os.path.basename(latest)}")
        with tarfile.open(latest, "r:gz") as tar:
            tar.extractall(RESTORE_DIR)

        self.set_status("Restoring latest backup...")
        code = self.run_command_and_log([ludusavi(), "restore", "--path", RESTORE_DIR, "--force"])
        if code != 0:
            self.set_status("Restore latest failed")
            return

        self.set_status("Restore latest completed")

    def restore_all(self):
        threading.Thread(target=self._restore_all_worker, daemon=True).start()

    def _restore_all_worker(self):
        self._sync_library_worker()

        archives = sorted(
            [os.path.join(LOCAL_BACKUP_DIR, f) for f in os.listdir(LOCAL_BACKUP_DIR) if f.endswith(".tar.gz")]
        )
        if not archives:
            self.set_status("No local archives found")
            return

        if os.path.isdir(RESTORE_DIR):
            shutil.rmtree(RESTORE_DIR, ignore_errors=True)
        os.makedirs(RESTORE_DIR, exist_ok=True)

        self.set_status("Extracting all archives...")
        for archive in archives:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(RESTORE_DIR)

        self.set_status("Restoring all backups...")
        code = self.run_command_and_log([ludusavi(), "restore", "--path", RESTORE_DIR, "--force"])
        if code != 0:
            self.set_status("Restore all failed")
            return

        self.set_status("Restore all completed")

    def restore_selected_game(self):
        selection = self.history_list.curselection()
        if not selection:
            messagebox.showwarning("Error", "Select a backup archive first.")
            return

        archive_name = self.history_list.get(selection[0])
        if "_" not in archive_name:
            messagebox.showwarning("Error", "Could not infer game name from archive.")
            return

        game_name = archive_name.rsplit("_", 2)[0]
        threading.Thread(target=self._restore_selected_game_worker, args=(game_name,), daemon=True).start()

    def _restore_selected_game_worker(self, game_name):
        self._sync_library_worker()

        pattern = f"{game_name}_"
        archives = sorted(
            [
                os.path.join(LOCAL_BACKUP_DIR, f)
                for f in os.listdir(LOCAL_BACKUP_DIR)
                if f.startswith(pattern) and f.endswith(".tar.gz")
            ]
        )

        if not archives:
            self.set_status(f"No local archive found for {game_name}")
            return

        latest = archives[-1]

        if os.path.isdir(RESTORE_DIR):
            shutil.rmtree(RESTORE_DIR, ignore_errors=True)
        os.makedirs(RESTORE_DIR, exist_ok=True)

        self.set_status(f"Extracting latest archive for {game_name}...")
        with tarfile.open(latest, "r:gz") as tar:
            tar.extractall(RESTORE_DIR)

        self.set_status(f"Restoring latest backup for {game_name}...")
        code = self.run_command_and_log([ludusavi(), "restore", "--path", RESTORE_DIR, "--force"])
        if code != 0:
            self.set_status(f"Restore failed for {game_name}")
            return

        self.set_status(f"Restore completed for {game_name}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
