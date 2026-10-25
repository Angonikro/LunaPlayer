#!/usr/bin/env python3
"""LunaPlayer entry point."""
import sys
from app.gtk_compat import require_gtk
require_gtk()
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from app.controller_client import client
from ui.main_window import LunaPlayerWindow

class LunaPlayerApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="de.lunaplayer.LunaPlayer")
        self.main_window = None
        client.start(self._controller_message)

    def _controller_message(self, command):
        GLib.idle_add(self._dispatch_controller_message, command)

    def _dispatch_controller_message(self, command):
        if command == "SHOW":
            if self.main_window is not None:
                self.main_window.present()
        elif command == "QUIT":
            if self.main_window is not None:
                self.main_window._quit_app()
        elif command == "TRAY_FAILED":
            if self.main_window is not None:
                self.main_window._tray_failed()
        elif command == "TRAY_READY":
            if self.main_window is not None:
                self.main_window._tray_ready()
        return GLib.SOURCE_REMOVE

    def do_activate(self):
        # Do not reuse an uninitialized/placeholder active window. This avoids
        # showing a blank window when activation is triggered by a desktop file.
        try:
            if self.main_window is None:
                self.main_window = LunaPlayerWindow(application=self)
            self.main_window.present()
        except Exception:
            import traceback
            from pathlib import Path
            log_dir = Path.home() / ".cache" / "lunaplayer"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "startup.log").open("a", encoding="utf-8") as log:
                log.write("\n--- Fehler beim Aktivieren von LunaPlayer ---\n")
                traceback.print_exc(file=log)
            raise

if __name__ == "__main__":
    app = LunaPlayerApp()
    raise SystemExit(app.run(sys.argv))
