# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [1.3.3] - 2025-01-31

### Behoben
- Kritischer Bug behoben: Versteckte Dateien in Unterordnern wurden fälschlicherweise extrahiert, auch wenn `--include-hidden` nicht gesetzt war
- Die Logik für das Durchsuchen von Unterordnern wurde korrigiert, sodass versteckte Dateien nur mit dem expliziten Flag extrahiert werden

## [1.3.2] - 2025-01-31

### Hinzugefügt
- Neue Option `--include-hidden` zum Einbeziehen versteckter Dateien (die mit . beginnen)
- Versteckte Dateien werden standardmäßig ignoriert, können aber jetzt optional einbezogen werden

### Behoben
- Git-spezifische Dateinamen (wie `index`, `HEAD`, `config`) werden jetzt nur noch ohne Erweiterung ignoriert
- `index.html`, `config.json` und ähnliche Dateien werden jetzt korrekt erkannt und nicht mehr fälschlicherweise ignoriert

### Geändert
- Verbesserte Filter-Logik für temporäre und System-Dateien
- Aktualisierte Dokumentation mit Beispielen für die neue Option

## [1.3.1] - 2025-01-28

### Hinzugefügt
- Automatische Bereinigung von Terminal-Escape-Sequenzen im Domain-Namensfeld

### Behoben
- Web-Link Analyse funktioniert jetzt korrekt auch bei komplexeren .webloc Dateien
- Verbesserte Fehlerbehandlung bei der Domain-Extraktion

## [1.3.0] - 2025-01-27

### Hinzugefügt
- Neue Option `--sort-by-type` zum automatischen Sortieren von Dateien in Typ-spezifische Ordner
- Dateien werden in Ordner wie PDF/, JPEG/, DOCX/ etc. organisiert
- Ähnliche Dateitypen werden intelligent zusammengefasst (z.B. jpg → JPEG/)
- Dateien ohne Erweiterung werden in OHNE_ERWEITERUNG/ gespeichert
- Die Option funktioniert mit allen anderen Filtern und Optionen

### Verbessert
- Erweiterte Hilfe-Dokumentation mit detaillierten Beispielen
- Bessere Strukturierung der Kommandozeilen-Hilfe

## [1.2.0] - 2025-01-26

### Hinzugefügt
- Dateityp-Filter mit `--type` Option zum selektiven Extrahieren bestimmter Dateitypen
- Domain-Filter mit `--domain` Option zum Filtern von Web-Links nach Domains
- Unterstützung für .url und .webloc Dateien
- Erweiterte Beispiele in der Dokumentation

### Verbessert
- Flexiblere Eingabe für Dateitypen (mit oder ohne Punkt, case-insensitive)
- Bessere Fehlerbehandlung bei der Analyse von Web-Links

## [1.1.0] - 2025-01-25

### Hinzugefügt
- Dry-Run Modus mit `--dry-run` Option
- Verbesserte Fortschrittsanzeige mit Prozentangaben
- Detailliertere Statistiken nach Abschluss

### Behoben
- Verbesserte Behandlung von Sonderzeichen in Dateinamen
- Stabilere ESC-Tasten-Erkennung auf verschiedenen Terminals

## [1.0.0] - 2025-01-24

### Erstveröffentlichung
- Grundlegende Funktionalität zum Extrahieren von Dateien aus Unterordnern
- Sicherheitsprüfung für Desktop, Downloads und Documents Ordner
- Intelligente Duplikat-Behandlung mit automatischer Umbenennung
- Tiefensteuerung mit `--depth` Option
- ESC-Taste zum Abbrechen
- Undo-Funktion zum Rückgängigmachen der letzten Operation
- Automatisches Löschen leerer Ordner
- Benutzerbestätigung vor dem Start
- Detailliertes Feedback und Zusammenfassung