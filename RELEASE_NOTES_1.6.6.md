# LunaPlayer 1.6.6

## Korrektur: TV-M3U-Sendernamen

- IPTV-M3U-Dateien mit `#EXTINF` zeigen jetzt den darin gespeicherten Sendernamen an.
- URLs wie `master.m3u8` oder `index.m3u8` werden nicht mehr als Sendername angezeigt, wenn ein M3U-Sendername vorhanden ist.
- Normale M3U-Playlists für MP3 und andere Audiodateien bleiben vollständig kompatibel.
- Die eigentliche Wiedergabe verwendet weiterhin unverändert den originalen Dateipfad bzw. die Stream-URL.
