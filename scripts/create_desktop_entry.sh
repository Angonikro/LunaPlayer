#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
APP_PATH="$PROJECT_DIR/main.py"
PROJECT_ICON="$PROJECT_DIR/data/icons/lunaplayer.svg"
SYSTEM_ENTRY="/usr/share/applications/lunaplayer.desktop"
SYSTEM_ICON="/usr/share/icons/hicolor/scalable/apps/lunaplayer.svg"

# Honor the desktop folder configured by the user.
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [ -f "$HOME/.config/user-dirs.dirs" ]; then
    . "$HOME/.config/user-dirs.dirs"
    if [ -n "${XDG_DESKTOP_DIR:-}" ]; then
        case "$XDG_DESKTOP_DIR" in
            '$HOME'/*) DESKTOP_DIR="$HOME/$(printf '%s' "$XDG_DESKTOP_DIR" | sed "s|^\\$HOME/||")" ;;
            '$HOME') DESKTOP_DIR="$HOME" ;;
            *) DESKTOP_DIR="$XDG_DESKTOP_DIR" ;;
        esac
    fi
fi
mkdir -p "$DESKTOP_DIR"
DEST="$DESKTOP_DIR/LunaPlayer.desktop"

# Only the packaged installation may use the system launcher.
# When run from a ZIP/extracted folder, always point to this folder's main.py,
# even if an older DEB version is installed on the same machine.
if [ "$PROJECT_DIR" = "/usr/share/lunaplayer" ]; then
    if [ ! -r "$SYSTEM_ENTRY" ]; then
        echo "System-Desktop-Starter nicht gefunden: $SYSTEM_ENTRY" >&2
        exit 1
    fi
    cp "$SYSTEM_ENTRY" "$DEST"
    if [ -r "$SYSTEM_ICON" ]; then
        if grep -q '^Icon=' "$DEST"; then
            sed "s|^Icon=.*|Icon=$SYSTEM_ICON|" "$DEST" > "$DEST.tmp"
            mv "$DEST.tmp" "$DEST"
        else
            printf '\nIcon=%s\n' "$SYSTEM_ICON" >> "$DEST"
        fi
    fi
else
    if [ ! -r "$APP_PATH" ]; then
        echo "LunaPlayer main.py nicht gefunden: $APP_PATH" >&2
        exit 1
    fi
    if [ -r "$PROJECT_ICON" ]; then ICON_PATH="$PROJECT_ICON"; else ICON_PATH="audio-player"; fi
    printf '[Desktop Entry]\nVersion=1.0\nType=Application\nName=LunaPlayer (ZIP)\nComment=Startet LunaPlayer aus diesem entpackten Ordner\nExec=/usr/bin/python3 "%s"\nIcon=%s\nTerminal=false\nCategories=AudioVideo;Audio;Player;\nStartupNotify=true\n' "$APP_PATH" "$ICON_PATH" > "$DEST"
fi

chmod +x "$DEST"
if command -v gio >/dev/null 2>&1; then gio set "$DEST" metadata::trusted true 2>/dev/null || true; fi
echo "LunaPlayer-Desktop-Starter erstellt: $DEST"
if [ "$PROJECT_DIR" != "/usr/share/lunaplayer" ]; then
    echo "Dieser Starter verwendet die ZIP-Version aus: $PROJECT_DIR"
    echo "Er ist unabhängig von einer zusätzlich installierten DEB-Version."
fi
echo "Falls der Desktop nachfragt, den Starter als vertrauenswürdig markieren."
