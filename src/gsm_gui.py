#!/usr/bin/env python3
import gi
import subprocess
import threading
import os
import shutil

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(BASE_DIR, "gsm_cli.sh")
BACKUP_DIR = os.path.expanduser("~/game-backups")
CONFIG_FILE = os.path.expanduser("~/.config/gsm/config.toml")
TEMP_DETECT_DIR = "/tmp/gsm_detect_gui"
TEMP_RESTORE_DIR = "/tmp/gsm_restore_gui"

CSS = b"""
window {
    background: #1e1e2e;
    color: #cdd6f4;
    font-family: JetBrains Mono, monospace;
    font-size: 11pt;
}

headerbar {
    background: #181825;
    color: #cdd6f4;
    border: none;
    box-shadow: none;
}

label {
    color: #cdd6f4;
}

.title-label {
    font-size: 20pt;
    font-weight: 700;
    color: #f5e0dc;
}

.subtitle-label {
    color: #a6adc8;
    font-size: 10pt;
}

.section-title {
    font-size: 11pt;
    font-weight: 700;
    color: #f5e0dc;
}

.card {
    background: #181825;
    border-radius: 14px;
    border: 1px solid #313244;
    padding: 14px;
}

.status-card {
    background: #11111b;
    border-radius: 12px;
    border: 1px solid #313244;
    padding: 12px;
}

.primary-button {
    background: #89b4fa;
    color: #11111b;
    border-radius: 10px;
    border: none;
    padding: 10px 14px;
    font-weight: 700;
}

.primary-button:hover {
    background: #74c7ec;
}

.secondary-button {
    background: #313244;
    color: #cdd6f4;
    border-radius: 10px;
    border: 1px solid #45475a;
    padding: 10px 14px;
    font-weight: 600;
}

.secondary-button:hover {
    background: #45475a;
}

textview, treeview {
    background: #11111b;
    color: #cdd6f4;
    border-radius: 10px;
    border: 1px solid #313244;
}

entry {
    background: #11111b;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px;
}

progressbar trough {
    background: #313244;
    border-radius: 999px;
    min-height: 10px;
}

progressbar progress {
    background: #89b4fa;
    border-radius: 999px;
    min-height: 10px;
}
"""


def get_config(key):
    if not os.path.exists(CONFIG_FILE):
        return ""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(key) and "=" in line:
                return line.split("=", 1)[1].strip().strip('"')
    return ""


class GSM(Gtk.Window):
    def __init__(self):
        super().__init__(title="GSM")
        self.set_default_size(1050, 720)
        self.set_border_width(16)
        self.running = False

        self.apply_css()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(root)

        root.pack_start(self.build_header(), False, False, 0)
        root.pack_start(self.build_status_card(), False, False, 0)
        root.pack_start(self.build_buttons(), False, False, 0)
        root.pack_start(self.build_main_content(), True, True, 0)
        root.pack_start(self.build_logs(), True, True, 0)

        self.refresh_history()

    def apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build_header(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        title = Gtk.Label(label="GSM")
        title.set_xalign(0)
        title.get_style_context().add_class("title-label")

        subtitle = Gtk.Label(label="Game Save Manager")
        subtitle.set_xalign(0)
        subtitle.get_style_context().add_class("subtitle-label")

        box.pack_start(title, False, False, 0)
        box.pack_start(subtitle, False, False, 0)
        return box

    def build_status_card(self):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.get_style_context().add_class("status-card")

        self.status = Gtk.Label(label="Idle")
        self.status.set_xalign(0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)

        frame.pack_start(self.status, False, False, 0)
        frame.pack_start(self.progress, False, False, 0)
        return frame

    def build_buttons(self):
        box = Gtk.Box(spacing=10)

        self.btn_backup = self.make_button("Automatic Backup", self.start_backup, primary=True)
        self.btn_manual = self.make_button("Manual Backup", self.start_manual_backup)
        self.btn_restore = self.make_button("Restore Selected", self.start_restore_selected)
        self.btn_sync = self.make_button("Sync", self.start_sync)
        self.btn_refresh = self.make_button("Refresh History", self.refresh_history)
        self.btn_settings = self.make_button("Settings", self.open_settings)

        box.pack_start(self.btn_backup, True, True, 0)
        box.pack_start(self.btn_manual, True, True, 0)
        box.pack_start(self.btn_restore, True, True, 0)
        box.pack_start(self.btn_sync, True, True, 0)
        box.pack_start(self.btn_refresh, True, True, 0)
        box.pack_start(self.btn_settings, True, True, 0)

        return box

    def build_main_content(self):
        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        left_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left_card.get_style_context().add_class("card")

        left_title = Gtk.Label(label="Detected Games")
        left_title.set_xalign(0)
        left_title.get_style_context().add_class("section-title")
        left_card.pack_start(left_title, False, False, 0)

        self.detected_store = Gtk.ListStore(str)
        self.detected_view = Gtk.TreeView(model=self.detected_store)
        renderer1 = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn("Game", renderer1, text=0)
        self.detected_view.append_column(col1)

        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        left_scroll.add(self.detected_view)
        left_card.pack_start(left_scroll, True, True, 0)

        right_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right_card.get_style_context().add_class("card")

        right_title = Gtk.Label(label="Backup History")
        right_title.set_xalign(0)
        right_title.get_style_context().add_class("section-title")
        right_card.pack_start(right_title, False, False, 0)

        info = Gtk.Label(label="Sync downloads cloud archives. Refresh History only reloads the local list.")
        info.set_xalign(0)
        right_card.pack_start(info, False, False, 0)

        self.history_store = Gtk.ListStore(str)
        self.history_view = Gtk.TreeView(model=self.history_store)
        renderer2 = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn("Archive", renderer2, text=0)
        self.history_view.append_column(col2)

        right_scroll = Gtk.ScrolledWindow()
        right_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        right_scroll.add(self.history_view)
        right_card.pack_start(right_scroll, True, True, 0)

        pane.pack1(left_card, resize=True, shrink=False)
        pane.pack2(right_card, resize=True, shrink=False)

        return pane

    def build_logs(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("card")

        title = Gtk.Label(label="Logs")
        title.set_xalign(0)
        title.get_style_context().add_class("section-title")
        card.pack_start(title, False, False, 0)

        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_monospace(True)
        self.log_buffer = self.log_view.get_buffer()

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(220)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.log_view)
        card.pack_start(scroll, True, True, 0)

        return card

    def make_button(self, text, callback, primary=False):
        btn = Gtk.Button(label=text)
        btn.connect("clicked", callback)
        btn.get_style_context().add_class("primary-button" if primary else "secondary-button")
        return btn

    def set_running(self, state):
        self.running = state
        for btn in [self.btn_backup, self.btn_manual, self.btn_restore, self.btn_sync, self.btn_refresh, self.btn_settings]:
            GLib.idle_add(btn.set_sensitive, not state)

    def log(self, msg):
        GLib.idle_add(self._log, msg)

    def _log(self, msg):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, msg + "\n")
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def set_status(self, text):
        GLib.idle_add(self.status.set_text, text)

    def set_progress(self, value):
        value = max(0.0, min(1.0, value))
        GLib.idle_add(self.progress.set_fraction, value)

    def clear_detected(self):
        GLib.idle_add(self.detected_store.clear)

    def add_detected_game(self, name):
        GLib.idle_add(self.detected_store.append, [name])

    def clear_history(self):
        GLib.idle_add(self.history_store.clear)

    def add_history_item(self, name):
        GLib.idle_add(self.history_store.append, [name])

    def refresh_history(self, *_args):
        self.clear_history()
        if os.path.isdir(BACKUP_DIR):
            files = sorted(
                [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")],
                reverse=True
            )
            for f in files:
                self.add_history_item(f)
        self.log("Local history refreshed.")

    def run_and_log(self, cmd):
        self.log("$ " + " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in proc.stdout:
            self.log(line.rstrip())
        return proc.wait()

    def start_backup(self, _widget):
        if not self.running:
            threading.Thread(target=self.backup_flow, daemon=True).start()

    def backup_flow(self):
        self.set_running(True)
        try:
            self.clear_detected()
            self.set_status("Detecting saves...")
            self.set_progress(0.05)

            if os.path.exists(TEMP_DETECT_DIR):
                shutil.rmtree(TEMP_DETECT_DIR)
            os.makedirs(TEMP_DETECT_DIR, exist_ok=True)

            code = self.run_and_log(["ludusavi", "backup", "--path", TEMP_DETECT_DIR, "--force"])
            if code != 0:
                self.set_status("Detection failed")
                self.set_progress(0.0)
                return

            self.set_progress(0.25)

            detected = []
            if os.path.isdir(TEMP_DETECT_DIR):
                for entry in sorted(os.listdir(TEMP_DETECT_DIR)):
                    full = os.path.join(TEMP_DETECT_DIR, entry)
                    if os.path.isdir(full):
                        detected.append(entry)
                        self.add_detected_game(entry)

            if not detected:
                self.log("No saves detected.")
                self.set_status("No saves detected")
                self.set_progress(0.0)
                return

            self.set_status(f"{len(detected)} game(s) detected")
            self.set_progress(0.45)

            self.set_status("Creating archives and uploading...")
            code = self.run_and_log([CLI, "backup"])
            if code != 0:
                self.set_status("Backup failed")
                self.set_progress(0.0)
                return

            self.set_progress(0.9)
            self.set_status("Refreshing local history...")
            self.refresh_history()

            self.set_progress(1.0)
            self.set_status("Backup completed")
        finally:
            self.set_running(False)

    def start_manual_backup(self, _widget):
        if not self.running:
            threading.Thread(target=self.manual_backup_flow, daemon=True).start()

    def manual_backup_flow(self):
        self.set_running(True)
        try:
            chooser = Gtk.FileChooserDialog(
                title="Select save folder",
                parent=self,
                action=Gtk.FileChooserAction.SELECT_FOLDER
            )
            chooser.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
            response = chooser.run()
            save_path = chooser.get_filename() if response == Gtk.ResponseType.OK else None
            chooser.destroy()

            if not save_path:
                self.set_status("Manual backup cancelled")
                return

            dialog = Gtk.Dialog(title="Game Name", transient_for=self, flags=0)
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )

            content = dialog.get_content_area()
            entry = Gtk.Entry()
            entry.set_placeholder_text("Enter game name")
            content.add(entry)
            dialog.show_all()

            response = dialog.run()
            game_name = entry.get_text().strip() if response == Gtk.ResponseType.OK else ""
            dialog.destroy()

            if not game_name:
                self.set_status("Manual backup cancelled")
                return

            self.set_status("Running manual backup...")
            self.set_progress(0.3)

            code = self.run_and_log([CLI, "manual-backup", save_path, game_name])
            if code != 0:
                self.set_status("Manual backup failed")
                self.set_progress(0.0)
                return

            self.set_progress(1.0)
            self.set_status("Manual backup completed")
            self.refresh_history()
        finally:
            self.set_running(False)

    def start_restore_selected(self, _widget):
        if self.running:
            return

        selection = self.history_view.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter is None:
            self.set_status("Select a backup first")
            return

        filename = model[treeiter][0]
        threading.Thread(target=self.restore_selected_flow, args=(filename,), daemon=True).start()

    def restore_selected_flow(self, filename):
        self.set_running(True)
        try:
            archive_path = os.path.join(BACKUP_DIR, filename)

            if not os.path.isfile(archive_path):
                self.set_status("Backup file not found")
                return

            self.set_status(f"Preparing restore for {filename}...")
            self.set_progress(0.2)

            if os.path.exists(TEMP_RESTORE_DIR):
                shutil.rmtree(TEMP_RESTORE_DIR)
            os.makedirs(TEMP_RESTORE_DIR, exist_ok=True)

            tar_proc = subprocess.run(
                ["tar", "-xzf", archive_path, "-C", TEMP_RESTORE_DIR],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            if tar_proc.stdout:
                self.log(tar_proc.stdout.rstrip())

            if tar_proc.returncode != 0:
                self.set_status("Extraction failed")
                self.set_progress(0.0)
                return

            self.set_progress(0.65)
            self.set_status("Restoring save...")
            code = self.run_and_log(["ludusavi", "restore", "--path", TEMP_RESTORE_DIR, "--force"])

            if code != 0:
                self.set_status("Restore failed")
                self.set_progress(0.0)
                return

            self.set_progress(1.0)
            self.set_status("Restore completed")
        finally:
            self.set_running(False)

    def start_sync(self, _widget):
        if not self.running:
            threading.Thread(target=self.sync_flow, daemon=True).start()

    def sync_flow(self):
        self.set_running(True)
        try:
            self.set_status("Syncing cloud backups to the local backup library...")
            self.set_progress(0.2)

            code = self.run_and_log([CLI, "sync"])
            if code != 0:
                self.set_status("Sync failed")
                self.set_progress(0.0)
                return

            self.set_progress(1.0)
            self.set_status("Sync completed")
            self.refresh_history()
        finally:
            self.set_running(False)

    def open_settings(self, _widget):
        dialog = Gtk.Dialog(title="Settings", transient_for=self, flags=0)
        dialog.set_default_size(420, 220)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )

        box = dialog.get_content_area()
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=12)
        box.add(grid)

        remote_entry = Gtk.Entry()
        remote_entry.set_text(get_config("remote"))

        max_entry = Gtk.Entry()
        max_entry.set_text(get_config("max_backups_per_game"))

        schedule_entry = Gtk.Entry()
        schedule_entry.set_text(get_config("schedule"))

        grid.attach(Gtk.Label(label="Remote"), 0, 0, 1, 1)
        grid.attach(remote_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Max backups per game"), 0, 1, 1, 1)
        grid.attach(max_entry, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Schedule"), 0, 2, 1, 1)
        grid.attach(schedule_entry, 1, 2, 1, 1)

        hint = Gtk.Label(label='Examples: "*-*-* 22:00" or "*-*-* 07..12:00"')
        hint.set_xalign(0)
        grid.attach(hint, 0, 3, 2, 1)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            remote = remote_entry.get_text().strip()
            max_backups = max_entry.get_text().strip()
            schedule = schedule_entry.get_text().strip()

            if remote:
                self.run_and_log([CLI, "update-remote", remote])
            if max_backups:
                self.run_and_log([CLI, "update-max-backups", max_backups])
            if schedule:
                self.run_and_log([CLI, "update-schedule", schedule])

            self.set_status("Settings updated")

        dialog.destroy()


def main():
    if not os.path.exists(CLI):
        print("gsm_cli.sh not found")
        return

    if not os.access(CLI, os.X_OK):
        os.chmod(CLI, 0o755)

    win = GSM()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
