"""Video and optical-disc playback using VLC."""
from pathlib import Path
import shutil
import subprocess

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm", ".mpeg", ".mpg", ".ts", ".m2ts", ".wmv", ".flv", ".ogv", ".3gp"}
VIDEO_FILTER_LABEL = "Videodateien (MKV, MP4, AVI, MOV, TS, WebM …)"

def is_supported_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS

def vlc_path():
    return shutil.which("vlc")

def _vlc():
    exe = vlc_path()
    if not exe:
        raise RuntimeError("VLC ist nicht installiert. Installiere es mit: sudo apt install vlc")
    return exe

def play_video(paths):
    if not paths:
        raise ValueError("Keine Videodatei ausgewählt.")
    exe = _vlc()
    args = [exe, "--no-one-instance", "--playlist-enqueue"]
    args.extend(str(Path(item).expanduser().resolve()) for item in paths)
    return subprocess.Popen(args, start_new_session=True)

def play_disc(kind, device="/dev/sr0"):
    exe = _vlc()
    if not Path(device).exists():
        raise RuntimeError(f"Laufwerk nicht gefunden: {device}")
    if kind == "dvd":
        source = f"dvd://{device}"
    elif kind == "bluray":
        source = f"bluray://{device}"
    else:
        raise ValueError("Unbekannter Disc-Typ.")
    return subprocess.Popen([exe, "--no-one-instance", source], start_new_session=True)
