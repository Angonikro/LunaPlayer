# LunaPlayer 1.6.5

## Änderung
Der Auswurf optischer Datenträger erfolgt jetzt asynchron im Hintergrund:
- Audio-CD
- DVD
- Blu-ray

Während `eject` auf das Laufwerk wartet, bleibt die GTK-Oberfläche bedienbar. Die Auswurftaste wird bis zum Abschluss deaktiviert; Erfolg oder Fehler werden anschließend in der Oberfläche angezeigt.

## Bewusst unverändert
- VLC-Wiedergabe und Lautstärkeregelung
- DVD-/Blu-ray-Start und Disc-Erkennung
- CD-Erkennung und CD-Wiedergabe
- Vollbild- und Fensterlogik
