# LunaPlayer 1.3.4 – Versionshinweise

## Automatische Cover-Erkennung

- Eingebettete Cover bleiben erste Wahl.
- Wenn kein eingebettetes Cover vorhanden ist, sucht LunaPlayer im Ordner des Titels nach `cover`, `folder`, `front`, `album`, `albumart` oder `artwork` als JPG/PNG/WebP.
- Falls kein typischer Covername vorhanden ist und genau ein Bild im Ordner liegt, wird dieses als Cover verwendet.
- Die Cover-Zuordnung ist nur für die Anzeige; Audiodateien werden nicht verändert.
- Keine neuen Python-Abhängigkeiten.

Die Version basiert auf LunaPlayer 1.3.3 und behält Wiedergabe, Tray-Funktion und Sprachumschaltung bei.
