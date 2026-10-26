# Änderungsprotokoll

## Version 1.3.4
- Fehlende Cover werden beim Anzeigen eines Titels automatisch über Bilddateien im selben Musikordner ergänzt.
- Eingebettete Cover haben weiterhin Vorrang; Audio-Dateien werden nicht verändert.
- Übliche Namen wie `cover.jpg`, `folder.jpg`, `front.jpg` und `album.jpg` sowie PNG-/WebP-Varianten werden erkannt.


## Version 1.3.3
- M4A- und MP4-Dateien ohne Videospur als unterstützte Audioformate ergänzt.
- Dateiauswahl, Musikordner-Suche und Wiedergabelisten berücksichtigen die neuen Endungen.
- Vorhandene GStreamer-Wiedergabe und Paketabhängigkeiten bleiben unverändert.


## Version 1.3.2
- Skript zum Erstellen eines Desktop-Starters für ZIP-/Quellcode-Installationen und installierte Debian-Pakete hinzugefügt.
- README um die erforderlichen `chmod +x`-Befehle und die Einrichtung des Desktop-Starters ergänzt.
- Starter-Skripte in das ZIP-Archiv und das Debian-Paket aufgenommen.

## Version 1.3.1
- Programmversion, Info-Dialog, Debian-Paket-Metadaten und Dokumentation auf denselben Versionsstand gebracht.
- Das deutsch-/englischsprachige Handbuch und das Release-Paket aktualisiert.
- Die Sprachauswahl Deutsch/Englisch und die gespeicherte Spracheinstellung aus Version 1.3.0 beibehalten.

## Version 1.3.0 – Sprachaktualisierung
- Sprachauswahl Deutsch/Englisch in der Kopfzeile des Players ergänzt.
- Die gewählte Sprache wird in `~/.config/lunaplayer/settings.json` gespeichert.
- Englische Beschriftungen für das System-Tray-Menü ergänzt.

## 1.3.4 FIX1
- Fix Debian installation not refreshing the desktop menu and icon caches.
- Add post-install and removal cache refresh scripts; keep the application version at 1.3.4.
