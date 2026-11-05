#!/usr/bin/env python3
"""LunaPlayer host: Tkinter owns the lifecycle and GTK 3 tray, like LunaKalender.
The GTK 4 player UI runs as a child process so GTK 3 and GTK 4 never share a process.
"""
import os, sys, socket, socketserver, threading, subprocess, signal, time, json
from pathlib import Path
import tkinter as tk
from app.settings import load_settings

VERSION = "1.6.7"
SOCKET_PATH = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"lunaplayer-controller-{os.getuid()}.sock"

class TrayHost:
    def __init__(self, root):
        self.root = root
        self.language = load_settings().get("language", "de")
        self.icon = None
        self.menu = None
        self.Gtk = self.GLib = self.GdkPixbuf = None
        self._ready = threading.Event()
        self._error = None
        self._gtk_thread = None
        self.enabled = False
        self._load_gtk()

    def _load_gtk(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib, GdkPixbuf
        self.Gtk, self.GLib, self.GdkPixbuf = Gtk, GLib, GdkPixbuf

    def start(self):
        if self.enabled and self.icon:
            return True
        self.enabled = True
        self._ready.clear(); self._error = None
        def run_gtk_tray():
            try:
                Gtk, GLib, GdkPixbuf = self.Gtk, self.GLib, self.GdkPixbuf
                icon_path = Path(__file__).resolve().parent / "app" / "tray_icon.png"
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_path), 24, 24, True)
                icon = Gtk.StatusIcon()
                icon.set_title("LunaPlayer")
                icon.set_tooltip_text("LunaPlayer")
                icon.set_from_pixbuf(pixbuf)
                icon.connect("activate", lambda *_: self.root.after(0, lambda: self.send_to_child("SHOW")))
                menu = Gtk.Menu()
                show_item = Gtk.MenuItem(label="Open LunaPlayer" if self.language == "en" else "LunaPlayer öffnen")
                show_item.connect("activate", lambda *_: self.root.after(0, lambda: self.send_to_child("SHOW")))
                menu.append(show_item)
                quit_item = Gtk.MenuItem(label="Quit LunaPlayer" if self.language == "en" else "LunaPlayer beenden")
                quit_item.connect("activate", lambda *_: self.root.after(0, self.quit_from_tray))
                menu.append(quit_item); menu.show_all()
                icon.connect("popup-menu", lambda _icon, button, when: menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, when))
                icon.set_visible(True)
                self.icon, self.menu = icon, menu
                self._ready.set()
                Gtk.main()
            except Exception as exc:
                self._error = str(exc); self._ready.set()
        self._gtk_thread = threading.Thread(target=run_gtk_tray, daemon=True, name="LunaPlayer-GTK-Tray")
        self._gtk_thread.start()
        self._ready.wait(4)
        if self._error or not self.icon:
            self.enabled = False
            return False
        return True

    def stop(self):
        self.enabled = False
        icon = self.icon; self.icon = None; self.menu = None
        if icon is not None:
            try: self.GLib.idle_add(icon.set_visible, False)
            except Exception: pass
        try: self.GLib.idle_add(self.Gtk.main_quit)
        except Exception: pass

    def send_to_child(self, command):
        if controller.connection:
            try:
                with controller.send_lock:
                    controller.connection.sendall((command + "\n").encode())
            except OSError:
                pass

    def quit_from_tray(self):
        self.send_to_child("QUIT")
        self.root.after(700, self.root.quit)

class ControllerServer:
    def __init__(self, root, tray):
        self.root, self.tray = root, tray
        self.connection = None
        self.send_lock = threading.Lock()
        self.connection_ready = threading.Event()
        self.pending_open = []
        self.pending_lock = threading.Lock()
        self.server = None
        self.thread = None

    def start(self):
        try: SOCKET_PATH.unlink()
        except FileNotFoundError: pass
        owner = self
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                is_child = False
                try:
                    first = self.rfile.readline()
                    if not first:
                        return
                    command = first.decode("utf-8", "replace").strip()
                    if command == "CHILD_HELLO":
                        is_child = True
                        owner.connection = self.request
                        owner.connection_ready.set()
                        with owner.pending_lock:
                            queued = list(owner.pending_open)
                            owner.pending_open.clear()
                        for pending in queued:
                            owner._send_to_connection(pending)
                    else:
                        owner.handle_external_command(command)
                    for raw in self.rfile:
                        command = raw.decode("utf-8", "replace").strip()
                        if is_child:
                            owner.root.after(0, lambda c=command: owner.handle_command(c))
                        else:
                            owner.handle_external_command(command)
                except (OSError, RuntimeError):
                    pass
                finally:
                    if is_child and owner.connection is self.request:
                        owner.connection = None
                        owner.connection_ready.clear()

        class Server(socketserver.ThreadingUnixStreamServer):
            daemon_threads = True
            allow_reuse_address = True
        self.server = Server(str(SOCKET_PATH), Handler)
        os.chmod(SOCKET_PATH, 0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="LunaPlayer-IPC")
        self.thread.start()

    def handle_external_command(self, command):
        if command.startswith("OPEN\t"):
            if self.connection is not None:
                self.root.after(0, lambda c=command: self._send_to_connection(c))
            else:
                with self.pending_lock:
                    self.pending_open.append(command)

    def wait_for_child(self, timeout=8):
        return self.connection_ready.wait(timeout)

    def handle_command(self, command):
        if command == "TRAY_ON":
            if not self.tray.start(): self.tray.send_to_child("TRAY_FAILED")
        elif command == "TRAY_OFF":
            self.tray.stop()
        elif command == "CHILD_QUIT":
            self.root.after(150, self.root.quit)
        elif command.startswith("OPEN\t"):
            # Preserve the JSON payload intact; the GTK child owns the playlist.
            self._send_to_connection(command)

    def _send_to_connection(self, command):
        if self.connection:
            try:
                with self.send_lock:
                    self.connection.sendall((command + "\n").encode())
            except OSError:
                pass

    def close(self):
        if self.tray is not None: self.tray.stop()
        if self.server:
            self.server.shutdown(); self.server.server_close()
        try: SOCKET_PATH.unlink()
        except OSError: pass


def _forward_files_to_running_instance(paths):
    """Send files to an already running LunaPlayer without replacing its IPC socket."""
    if not paths:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            sock.connect(str(SOCKET_PATH))
            payload = json.dumps([str(Path(x).expanduser().resolve()) for x in paths], ensure_ascii=False)
            sock.sendall(("OPEN\t" + payload + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def main():
    # A second launch must forward its files to the existing player. In
    # particular, it must not unlink/recreate the active controller socket.
    if _forward_files_to_running_instance(sys.argv[1:]):
        return
    root = tk.Tk()
    root.withdraw()
    try:
        tray = TrayHost(root)
        controller = ControllerServer(root, tray)
        globals()["controller"] = controller
        controller.start()
    except Exception as exc:
        # GTK 3 bindings are required only for tray use; the player still starts.
        tray = None
        controller = ControllerServer(root, None)
        globals()["controller"] = controller
        controller.start()
    settings = load_settings()
    if settings.get("tray_enabled", False) and tray and not tray.start():
        settings["tray_enabled"] = False
        from app.settings import save_settings
        save_settings(settings)
    child_path = Path(__file__).resolve().with_name("gtk_app.py")
    env = os.environ.copy(); env["LUNAPLAYER_CONTROLLER_SOCKET"] = str(SOCKET_PATH)
    # libVLC embeds video through X11; under Wayland use XWayland when available.
    if env.get("DISPLAY"):
        env["GDK_BACKEND"] = "x11"
    child = subprocess.Popen([sys.executable, str(child_path)], env=env)
    if sys.argv[1:] and controller.wait_for_child(10):
        payload = json.dumps([str(Path(x).expanduser().resolve()) for x in sys.argv[1:]], ensure_ascii=False)
        controller._send_to_connection("OPEN\t" + payload)
    def poll_child():
        if child.poll() is not None:
            root.quit(); return
        root.after(400, poll_child)
    root.after(400, poll_child)
    try: root.mainloop()
    finally:
        try: child.terminate(); child.wait(timeout=2)
        except Exception:
            try: child.kill()
            except Exception: pass
        controller.close()

if __name__ == "__main__":
    main()
