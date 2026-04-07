#!/usr/bin/env python3
import gi
import os
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

THEME_FILE = os.path.expanduser("~/.config/gsm/theme.toml")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLI_PATH = os.path.join(BASE_DIR, "gsm_cli.sh")


def read_kv(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


theme = read_kv(THEME_FILE)

bg = theme.get("bg", "#0d0f12")
fg = theme.get("fg", "#cdd6f4")
accent = theme.get("accent", "#89b4fa")
panel = theme.get("panel", "#1e1e2e")
font_family = theme.get("font_family", "JetBrains Mono")
font_size = theme.get("font_size", "11")

css = f"""
window {{
    background: {bg};
    color: {fg};
    font-family: {font_family};
    font-size: {font_size}px;
}}

headerbar {{
    background: {panel};
    color: {fg};
    border: none;
}}

button {{
    background: {panel};
    color: {fg};
    border-radius: 12px;
    padding: 12px;
    border: 1px solid {accent};
}}

button:hover {{
    background: {accent};
    color: {bg};
}}

label {{
    color: {fg};
}}

frame {{
    border: 1px solid {accent};
    border-radius: 10px;
    padding: 12px;
}}
""".encode("utf-8")


class GSMWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="GSM")
        self.set_default_size(560, 420)
        self.set_border_width(16)

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "GSM"
        header.props.subtitle = "Game Save Manager"
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(root)

        banner = Gtk.Label()
        banner.set_xalign(0)
        banner.set_markup(
            "<span font_desc='{} 12'>GSM\nminimal • modular • syncable</span>".format(font_family)
        )
        root.pack_start(banner, False, False, 0)

        frame = Gtk.Frame(label="Actions")
        root.pack_start(frame, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(12)
        frame.add(box)

        self.add_button(box, "Automatic Backup", self.on_backup_clicked)
        self.add_button(box, "Manual Backup", self.on_manual_backup_clicked)
        self.add_button(box, "Restore Latest", self.on_restore_clicked)
        self.add_button(box, "Sync From Cloud", self.on_sync_clicked)

        self.output = Gtk.TextView()
        self.output.set_editable(False)
        self.output.set_cursor_visible(False)
        self.output.set_monospace(True)
        self.output_buffer = self.output.get_buffer()

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(180)
        scroller.add(self.output)
        root.pack_start(scroller, True, True, 0)

    def add_button(self, box, text, callback):
        btn = Gtk.Button(label=text)
        btn.connect("clicked", callback)
        box.pack_start(btn, False, False, 0)

    def log(self, text):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, text + "\n")

    def run_command(self, args):
        self.log("$ " + " ".join(args))
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            output = result.stdout.strip()
            if output:
                self.log(output)
            if result.returncode == 0:
                self.show_message("Success", "Operation completed successfully.")
            else:
                self.show_message("Error", "Operation failed. Check output for details.")
        except Exception as e:
            self.log(str(e))
            self.show_message("Error", str(e))

    def show_message(self, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def on_backup_clicked(self, widget):
        self.run_command([CLI_PATH, "backup"])

    def on_manual_backup_clicked(self, widget):
        chooser = Gtk.FileChooserDialog(
            title="Select save directory",
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
            return

        dialog = Gtk.Dialog(title="Game name", transient_for=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        entry = Gtk.Entry()
        entry.set_placeholder_text("Enter game name")
        box = dialog.get_content_area()
        box.add(entry)
        dialog.show_all()

        response = dialog.run()
        game_name = entry.get_text().strip() if response == Gtk.ResponseType.OK else None
        dialog.destroy()

        if not game_name:
            return

        self.run_command([CLI_PATH, "manual-backup", save_path, game_name])

    def on_restore_clicked(self, widget):
        self.run_command([CLI_PATH, "restore"])

    def on_sync_clicked(self, widget):
        self.run_command([CLI_PATH, "sync"])


def main():
    if not os.path.exists(CLI_PATH):
        print("gsm_cli.sh not found")
        return
    if not os.access(CLI_PATH, os.X_OK):
        os.chmod(CLI_PATH, 0o755)

    win = GSMWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
