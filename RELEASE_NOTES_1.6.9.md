# LunaPlayer 1.6.9

## Änderungen
- LunaPlayer wird in Debian als Audio- und Videoplayer für unterstützte MIME-Typen registriert.
- Audio- und Videodateien können über „Öffnen mit“ mit LunaPlayer geöffnet werden.
- LunaPlayer kann in den Systemeinstellungen bzw. mit `xdg-mime` als Standardplayer ausgewählt werden.
- Die Installation ändert bestehende Standardanwendungen nicht automatisch.
- Die Desktop-MIME-Datenbank wird bei Installation und Entfernung aktualisiert.

## Fehlerkorrektur
- Beim Öffnen von `.m3u`- und `.m3u8`-Dateien aus dem Dateimanager werden die Playlist-Einträge jetzt geladen statt die Playlist-Datei als Audiodatei zu behandeln.
- Lokale Audiodateien in Playlists starten über GStreamer; Stream-URLs verwenden weiterhin den eingebetteten VLC-Player.
- Leere oder nicht unterstützte Playlists stoppen eine vorherige Wiedergabe und zeigen eine Statusmeldung.
- M3U/M3U8-Dateitypen sind in der Desktop-Dateizuordnung registriert.
