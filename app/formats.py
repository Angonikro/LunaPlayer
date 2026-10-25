"""Supported audio formats and default music-folder discovery."""
from pathlib import Path
import os
import subprocess

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".mp4"}
AUDIO_FILTER_LABEL = "Audiodateien (MP3, WAV, OGG, M4A, MP4-Audio)"


def is_supported_audio(path):
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def find_default_music_folder():
    """Find the user's configured Music directory, then common German/English names."""
    home = Path.home()
    # Respect XDG user-dir configuration if available.
    try:
        result = subprocess.run(
            ["xdg-user-dir", "MUSIC"], capture_output=True, text=True, timeout=2
        )
        candidate = Path(result.stdout.strip()).expanduser()
        if result.returncode == 0 and candidate.is_dir():
            return str(candidate)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # Prefer localized folder names, but only choose folders that exist.
    for name in ("Musik", "Music", "music", "musik"):
        candidate = home / name
        if candidate.is_dir():
            return str(candidate)

    # If no music folder exists yet, use ~/Music as the default target.
    return str(home / "Music")


def scan_folder(folder):
    root = Path(folder).expanduser()
    if not root.is_dir():
        return []
    try:
        return sorted(
            (str(p) for p in root.rglob("*") if p.is_file() and is_supported_audio(p)),
            key=str.casefold,
        )
    except (OSError, PermissionError):
        return []
