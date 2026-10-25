"""User settings stored outside the installation directory."""
import json
from pathlib import Path
from app.formats import find_default_music_folder

CONFIG_DIR = Path.home() / ".config" / "lunaplayer"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
DEFAULT_MUSIC_FOLDER = find_default_music_folder()
DEFAULTS = {
    "volume": 0.75,
    "language": "de",
    "audio_device": "",
    "dark_mode": True,
    "last_folder": DEFAULT_MUSIC_FOLDER,
    "music_folder": DEFAULT_MUSIC_FOLDER,
    "cd_device": "/dev/sr0",
    "tray_enabled": False,
    "close_to_tray": False,
    "equalizer_preset": "Neutral",
    "equalizer_bands": [0] * 10,
    "equalizer_profiles": {},
}

def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, ValueError, TypeError):
        return DEFAULTS.copy()

def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
