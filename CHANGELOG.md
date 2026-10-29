## 1.6.2
- VLC wiedergabe in die App integriert DVD Blu-ray Video
- In-App-Anleitung um Video-Dateien, Vollbild/Fenstermodus sowie DVD- und Blu-ray-Wiedergabe ergänzt.
- Englische Übersetzungen für alle neuen Hilfethemen ergänzt.
- Hinweise zu VLC, erforderlichen Disc-Bibliotheken und möglichen Einschränkungen bei geschützten Discs aufgenommen.

## 1.6.1
- Fehlende englische Übersetzungen für „Vollbild“ (Fullscreen) und „Fenster“ (Window) ergänzt.
- Keine Änderungen an Wiedergabe oder Disc-Funktionen.

## 1.6.0
- Programm- und Paketversion auf 1.6.0 vereinheitlicht; Grundlage ist der Quellcode von Version 1.5.42.
- Keine beabsichtigten Änderungen an DVD-/Blu-ray-Wiedergabe, Stopp/Neustart, Vollbildgröße oder Mauszeigersteuerung.

## 1.5.42
- Absturz beim automatischen Ausblenden des Mauszeigers im Vollbild behoben: Zum Aus- und Einblenden wird XFixes verwendet, statt wechselnden nativen Fenstern einen eigenen Mauszeiger zuzuweisen.
- Falls das Ausblenden des Mauszeigers nicht verfügbar ist, läuft die Wiedergabe mit sichtbarem Mauszeiger weiter.

## 1.5.41
- Bei Video-, DVD- und Blu-ray-Wiedergabe im Vollbild wird der Mauszeiger zusammen mit den Bedienelementen ausgeblendet und bei Mausbewegung wieder angezeigt.
- Keine beabsichtigten Änderungen an Wiedergabe, Disc-Funktionen, MP3-Funktionen oder Vollbildgröße.

## 1.5.40
- Auswurftaste ausschließlich im DVD-/Blu-ray-Dialog ergänzt. Das bisherige Wiedergabeverhalten bleibt erhalten.

## 1.5.37
- Im Fenstermodus wird beim Stoppen das VLC-Unterfenster ausgeblendet, bevor die Musikansicht wiederhergestellt wird – wie in Version 1.5.35.
- Im Vollbild bleibt das VLC-Unterfenster beim Stoppen eingebunden, damit der funktionierende Neustart der Wiedergabe erhalten bleibt.

## 1.5.34
- Stopp im Vollbild korrigiert: Die Wiedergabe wird beendet, ohne den Vollbildmodus zu verlassen.

## 1.5.33
- Beschriftung der Videomodus-Schaltfläche korrigiert: Im Vollbild wird „Fenster“, im normalen Modus „Vollbild“ angezeigt.

## 1.5.33
- Separates, schwebendes Bedienfenster für Videos im Vollbild ergänzt, da das native VLC-X11-Unterfenster normale GTK-Einblendungen überdeckt.
- Die Bedienelemente erscheinen bei Mausbewegung und werden nach zwei Sekunden ohne Bewegung ausgeblendet. Die funktionierende Vollbild- und Fenstergrößenlogik bleibt erhalten.

## 1.5.29
- Verkleinern des Vollbilds nach etwa einer Sekunde behoben: Solange Vollbild aktiv ist, verwendet die regelmäßige Fensterpositionierung nun die Routine für die Bildschirmgröße.

## 1.5.20
- Zwei getrennte Schaltflächen für Vollbild und Fenstermodus; jeweils nur die passende Aktion sichtbar. Versionsanzeige in der App aktualisiert.

## 1.5.3
- Korrigiert die Beschriftung der Vollbild-Schaltfläche, wenn der Vollbildmodus über GTK/Fenster-Manager verlassen wird.

## 1.5.2
- Korrigiert die Beschriftung der Vollbild-Schaltfläche nach der Rückkehr in den Fenstermodus. Die Beschriftung folgt jetzt dem expliziten Videomodus statt der verzögert aktualisierten GTK-Fenstereigenschaft.

## 1.5.1
- Vollbild-Schaltflächenbeschriftung nach dem Zurückwechseln zuverlässig synchronisieren.

## 1.5.0
- Vollbildwechsel neu umgesetzt: Fensterdekorationen werden ausgeblendet und der GTK-Vollbildaufruf nach der Layout-Änderung erneut angefordert.
- Rückkehr mit Esc oder „Fenster“ stellt die vorherige Oberfläche wieder her.

## 1.4.8
- Entfernt das separate VLC-Videofenster: VLC wird als deckende X11-Kindfläche innerhalb des LunaPlayer-Hauptfensters dargestellt.
- Videomodus blendet Musik-Bedienelemente aus; Escape beendet den Vollbildmodus.

## 1.4.7
- VLC-X11-Ausgabefläche auf deckenden 24-Bit-TrueColor-Visual umgestellt, um Transparenz/ Durchscheinen des Desktop-Inhalts zu vermeiden.
- README nur um einen gezielten Versionshinweis ergänzt.

## 1.4.6
- Verwendet einen neuen Ansatz für VLC: ein von LunaPlayer verwaltetes, separates Videofenster statt eines X11-Kindfensters über der GTK4-Musikoberfläche.
- Blendet MP3-Titelanzeige, Audio-Zeitleiste, Musiktransport und Lautstärkeregler während der Videowiedergabe aus.
- Vollbild wird nur auf das Videofenster angewendet; Esc beendet Vollbild bzw. schließt das Videofenster.
- Alte X11-Überlagerung in der Hauptoberfläche wird nicht mehr verwendet.

## 1.4.5
- VLC-X11-Videofläche mit explizitem schwarzem Hintergrund versehen.
- Position und Größe der nativen Videofläche nach Fenster-/Vollbildwechsel erneut synchronisieren.
- Versionshinweise zur Videoeinbettung aktualisiert.

## 1.4.4
- Verbessert die X11-VLC-Kindfensterfläche: vor dem ersten Bild schwarz löschen, über andere Kindflächen heben und X11-Aufrufe synchronisieren.
- Erneute Positionierung der VLC-Fläche nach dem Start der Wiedergabe.
- README-Struktur und vorhandene Musikfunktionen beibehalten.

## 1.4.3
- Bettet Video-, DVD- und Blu-ray-Wiedergabe mit libVLC direkt in das LunaPlayer-Fenster ein.
- Ergänzt Wiedergabe/Pause, Stopp, Positionsregler und Vollbild für Videos.
- Deklariert python3-vlc, libvlc5 und vlc-plugin-base als Debian-Abhängigkeiten.
- Bewahrt das bestehende README-Layout und die bisherigen Musikfunktionen.

# Changelog

## 1.4.2
- Korrigiert die Versionsanzeige in der App: Hauptfenster und Info-Dialog zeigen jetzt 1.4.2.
- Behält die VLC-Video-, DVD- und Blu-ray-Integration sowie alle bisherigen Musikfunktionen bei.

## 1.4.0
- Video-Wiedergabe mit VLC ergänzt.
- DVD-/Blu-ray-Start mit Laufwerksauswahl ergänzt.
- VLC-Abhängigkeit und optionale Disc-Bibliotheken im DEB deklariert.
- README um Formate, Installation und Disc-Hinweise erweitert.
- LunaPlayer bleibt der Programmname; bestehende Audiofunktionen bleiben erhalten.

## 1.3.4
- Automatische Cover-Erkennung aus dem Titelordner.

## 1.4.9
- Vollbildmodus für eingebettete Videos überarbeitet: blendet nicht benötigte App-Bereiche aus und stellt beim Verlassen das ursprüngliche Layout wieder her.
- Version 1.5.33: GTK-Elternzuordnung der Vollbild-Bedienelemente korrigiert und die schwebende Steuerleiste gestaltet.

## 1.5.39
- Die bestätigte Wiedergabe- und Vollbildimplementierung aus Version 1.5.37 als Grundlage für DVD und Blu-ray wiederhergestellt.
- DVD und Blu-ray verwenden weiterhin denselben eingebetteten VLC-Player und dieselben Wiedergabesteuerungen wie Videodateien.
- In dieser Version wurden weder die Vollbildgeometrie noch die Stopp-/Startlogik geändert.
