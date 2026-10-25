"""IPC client linking the GTK player window to the Tkinter/GTK3 tray host."""
import os, socket, threading, time
from pathlib import Path

SOCKET_PATH = Path(os.environ.get("LUNAPLAYER_CONTROLLER_SOCKET", "/tmp/lunaplayer-controller.sock"))
class ControllerClient:
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        self.callback = None
        self.thread = None
    def start(self, callback):
        self.callback = callback
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(str(SOCKET_PATH)); break
            except OSError:
                if self.sock:
                    self.sock.close()
                self.sock = None; time.sleep(.1)
        if not self.sock:
            return False
        self.thread = threading.Thread(target=self._read, daemon=True, name="LunaPlayer-Controller-Client")
        self.thread.start(); return True
    def _read(self):
        try:
            file = self.sock.makefile("r", encoding="utf-8")
            for line in file:
                command = line.strip()
                if command and self.callback:
                    self.callback(command)
        except OSError:
            pass
    def send(self, command):
        if not self.sock: return False
        try:
            with self.lock: self.sock.sendall((command + "\n").encode())
            return True
        except OSError: return False
    def close(self):
        try:
            if self.sock: self.sock.close()
        except OSError: pass

client = ControllerClient()
def send_command(command):
    return client.send(command)
