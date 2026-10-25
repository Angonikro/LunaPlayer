"""Linux optical-drive detection, modeled on LunaRipper's drive discovery.

Uses /dev/sr* discovery and cd-discid (the same practical detection approach used
by LunaRipper). Playback is handled by the GStreamer cdparanoiasrc pipeline.
"""
from pathlib import Path
import glob
import shutil
import subprocess


class AudioCD:
    def __init__(self, device="/dev/sr0"):
        self.device = device

    @staticmethod
    def discover_drives():
        devices = []
        for candidate in ["/dev/cdrom", *sorted(glob.glob("/dev/sr[0-9]*"))]:
            path = Path(candidate)
            if path.exists() and candidate not in devices:
                devices.append(candidate)
        return devices

    @staticmethod
    def inspect(device):
        """Return (is_audio_cd, track_count, message) using cd-discid when available."""
        if not Path(device).exists():
            return False, 0, f"CD-Laufwerk {device} nicht gefunden."
        if shutil.which("cd-discid"):
            try:
                proc = subprocess.run(
                    ["cd-discid", device], capture_output=True, text=True, timeout=10
                )
                parts = proc.stdout.strip().split()
                # cd-discid: discid track_count offsets... leadout_seconds
                if proc.returncode == 0 and len(parts) >= 4:
                    count = int(parts[1])
                    if count > 0 and len(parts) >= count + 3:
                        return True, count, f"Audio-CD erkannt: {count} Titel ({device})."
                detail = (proc.stderr or proc.stdout).strip()
                return False, 0, detail or "Keine Audio-CD erkannt. Bitte CD einlegen."
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                return False, 0, f"CD-Erkennung fehlgeschlagen: {exc}"
        if shutil.which("cdparanoia"):
            try:
                proc = subprocess.run(
                    ["cdparanoia", "-Q", "-d", device],
                    capture_output=True, text=True, timeout=12
                )
                output = proc.stdout + "\\n" + proc.stderr
                import re
                tracks = [int(m.group(1)) for m in re.finditer(r"^\\s*(\\d+)\\.", output, re.M)]
                if tracks:
                    return True, max(tracks), f"Audio-CD erkannt: {max(tracks)} Titel ({device})."
                return False, 0, "Keine Audio-CD erkannt oder CD-Laufwerk nicht lesbar."
            except (OSError, subprocess.SubprocessError) as exc:
                return False, 0, f"CD-Erkennung fehlgeschlagen: {exc}"
        return False, 0, "Erkennungswerkzeug fehlt. Bitte Paket cd-discid installieren."

    def detect(self):
        ok, count, message = self.inspect(self.device)
        return ok, message

    def eject(self):
        if not shutil.which("eject"):
            raise RuntimeError("Das Werkzeug 'eject' fehlt.")
        subprocess.run(["eject", self.device], check=True, timeout=8)
