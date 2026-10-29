"""Embedded VLC video and optical-disc playback for LunaPlayer's GTK window."""
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm", ".mpeg", ".mpg", ".ts", ".m2ts", ".wmv", ".flv", ".ogv", ".3gp"}
VIDEO_FILTER_LABEL = "Videodateien (MKV, MP4, AVI, MOV, TS, WebM …)"


def is_supported_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


class EmbeddedVLCPlayer:
    """Small libVLC wrapper; the GTK host supplies the native X11 window ID."""
    def __init__(self, on_finished=None):
        try:
            import vlc
        except Exception as exc:
            raise RuntimeError("Die VLC-Python-Bindings fehlen. Installiere python3-vlc und libvlc5.") from exc
        self.vlc = vlc
        self.instance = vlc.Instance("--no-video-title-show", "--quiet")
        if self.instance is None:
            raise RuntimeError("libVLC konnte nicht initialisiert werden.")
        self.player = self.instance.media_player_new()
        self.paths = []
        self.index = 0
        self.on_finished = on_finished
        self._xid = None
        self._pending = None
        self._disc_source = None
        self._stopped = False
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end)

    def set_window(self, xid):
        self._xid = int(xid)
        self.player.set_xwindow(self._xid)
        if self._pending:
            kind, value = self._pending
            self._pending = None
            if kind == "paths":
                self.play_paths(value)
            else:
                self.play_disc(*value)

    def play_paths(self, paths):
        self.paths = [str(Path(p).expanduser().resolve()) for p in paths]
        self.index = 0
        self._disc_source = None
        self._stopped = False
        if not self.paths:
            raise ValueError("Keine Videodatei ausgewählt.")
        if not self._xid:
            self._pending = ("paths", list(self.paths))
            return
        self._play_current()

    def play_disc(self, kind, device="/dev/sr0"):
        device = str(Path(device).expanduser())
        if not Path(device).exists():
            raise RuntimeError(f"Laufwerk nicht gefunden: {device}")
        if kind not in ("dvd", "bluray"):
            raise ValueError("Unbekannter Disc-Typ.")
        if not self._xid:
            self._pending = ("disc", (kind, device))
            return
        self.paths = []
        self.index = 0
        self._disc_source = f"{kind}://{device}"
        self._stopped = False
        source = self._disc_source
        media = self.instance.media_new(source)
        self.player.set_media(media)
        self.player.set_xwindow(self._xid)
        result = self.player.play()
        if result == -1:
            raise RuntimeError("VLC konnte die Disc nicht starten.")

    def _play_current(self):
        media = self.instance.media_new_path(self.paths[self.index])
        self.player.set_media(media)
        if self._xid:
            self.player.set_xwindow(self._xid)
        if self.player.play() == -1:
            raise RuntimeError(f"VLC konnte die Datei nicht öffnen: {self.paths[self.index]}")

    def _on_end(self, _event):
        if self.on_finished:
            self.on_finished()

    def next(self):
        if self.paths and self.index + 1 < len(self.paths):
            self.index += 1
            self._play_current()
            return True
        return False

    def pause_toggle(self):
        if self.player.is_playing():
            self.player.pause()
            return False
        # libVLC does not reliably resume a stopped media item with play() alone.
        # Reload the current file/disc after Stop, then start it from the beginning.
        if self._stopped:
            self._stopped = False
            if self.paths:
                self._play_current()
                return True
            if self._disc_source:
                media = self.instance.media_new(self._disc_source)
                self.player.set_media(media)
                if self._xid:
                    self.player.set_xwindow(self._xid)
                if self.player.play() == -1:
                    self._stopped = True
                    raise RuntimeError("VLC konnte die Disc nicht erneut starten.")
                return True
        self.player.play()
        return True

    def stop(self):
        self.player.stop()
        self._stopped = True

    def is_playing(self):
        return bool(self.player.is_playing())

    def position(self):
        return max(0.0, float(self.player.get_position()))

    def duration(self):
        return max(0, int(self.player.get_length() / 1000))

    def seek(self, fraction):
        self.player.set_position(max(0.0, min(1.0, float(fraction))))

    def close(self):
        try:
            self.player.stop()
            self.player.release()
        finally:
            self.instance.release()
