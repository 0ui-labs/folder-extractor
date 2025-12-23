# Folder Extractor

Ein sicheres Command-Line-Tool zum Extrahieren aller Dateien aus Unterordnern in den aktuellen Ordner. Perfekt zum Aufräumen tief verschachtelter Ordnerstrukturen.

## Features

- 🔒 **Sicherheitsprüfung**: Läuft nur in Desktop, Downloads oder Documents Ordnern
- 📁 **Intelligente Duplikat-Behandlung**: Automatische Umbenennung bei gleichnamigen Dateien
- 🎯 **Flexible Tiefensteuerung**: Bestimmen Sie, wie tief in die Ordnerstruktur gesucht werden soll
- 🧹 **Automatisches Aufräumen**: Entfernt leere Ordner nach dem Verschieben
- 📊 **Detailliertes Feedback**: Zeigt jeden Schritt und eine abschließende Zusammenfassung
- ✅ **Benutzer-Bestätigung**: Zeigt Vorschau und fragt vor dem Start nach Bestätigung
- 🛑 **ESC-Taste zum Abbrechen**: Jederzeit sicherer Abbruch möglich
- ↩️ **Undo-Funktion**: Macht die letzte Operation rückgängig
- 🔍 **Dry-Run Modus**: Zeigt was passieren würde, ohne es zu tun
- 📈 **Fortschrittsanzeige**: Prozentuale Anzeige während der Verschiebung
- 📎 **Dateityp-Filter**: Extrahiere nur bestimmte Dateitypen
- 🌐 **Domain-Filter**: Filtere Web-Links nach bestimmten Domains
- 🗂️ **Sortierung nach Typ**: Organisiere Dateien automatisch in Typ-Ordner
- 👻 **Versteckte Dateien**: Optional auch versteckte Dateien einbeziehen
- 🔄 **Intelligente Deduplizierung**: Erkennt identische Dateien anhand des Inhalts (Hash-Vergleich)
- 🌍 **Globale Deduplizierung**: Findet Duplikate im gesamten Zielordner

## Installation

### Systemweite Installation via pip

```bash
# Im Projektverzeichnis ausführen:
pip install .

# Oder für Entwicklung (editierbare Installation):
pip install -e .
```

Nach der Installation ist der Befehl `folder-extractor` systemweit verfügbar!

### Alternative: Direkte Nutzung ohne Installation

```bash
python folder_extractor.py [optionen]
```

## Verwendung

Nach der Installation können Sie das Tool in jedem erlaubten Ordner verwenden:

```bash
# Standard: Unbegrenzte Tiefe
folder-extractor

# Maximal 3 Ebenen tief suchen
folder-extractor --depth 3

# Nur erste Ebene
folder-extractor --depth 1

# Vorschau ohne tatsächliche Verschiebung
folder-extractor --dry-run

# Letzte Operation rückgängig machen
folder-extractor --undo

# Version anzeigen
folder-extractor --version

# Nur PDFs extrahieren (Ordnerstruktur bleibt erhalten)
folder-extractor --type pdf

# Mehrere Dateitypen
folder-extractor --type pdf,doc,docx

# Bilder aus maximal 2 Ebenen extrahieren
folder-extractor --type jpg,png,gif --depth 2

# Nur YouTube-Links extrahieren
folder-extractor --type url,webloc --domain youtube.com

# Links von mehreren Domains
folder-extractor --type url --domain youtube.com,github.com,reddit.com

# Dateien nach Typ sortieren
folder-extractor --sort-by-type

# Versteckte Dateien einbeziehen
folder-extractor --include-hidden

# Kombiniert: Versteckte PDFs sortiert extrahieren
folder-extractor --type pdf --include-hidden --sort-by-type

# Duplikate vermeiden (identischer Inhalt wird nicht dupliziert)
folder-extractor --deduplicate

# Globale Deduplizierung (prüft ALLE Dateien im Zielordner)
folder-extractor --global-dedup
```

### Dateityp-Filter

Mit der `--type` Option können Sie gezielt nur bestimmte Dateitypen extrahieren:
- Andere Dateien bleiben unberührt
- Die Ordnerstruktur bleibt vollständig erhalten
- Perfekt für selektives Organisieren

Beispiele für Dateitypen:
- **Dokumente**: pdf, doc, docx, txt, odt, md
- **Bilder**: jpg, jpeg, png, gif, bmp, svg
- **Web-Links**: url, webloc
- **Daten**: json, xml, csv, xlsx
- **Code**: py, js, java, cpp, html, css, md

### Domain-Filter für Web-Links

Mit der `--domain` Option können Sie Web-Links nach Domains filtern:
- Funktioniert nur zusammen mit `--type url` oder `--type webloc`
- Unterstützt Subdomains (youtube.com matcht auch m.youtube.com)
- Mehrere Domains mit Komma trennen

Beispiele:
```bash
# Alle YouTube-Links sammeln
folder-extractor --type url,webloc --domain youtube.com

# Links von bestimmten Entwickler-Seiten
folder-extractor --type url --domain github.com,stackoverflow.com

# Reddit-Links aus maximal 3 Ebenen
folder-extractor --type url,webloc --domain reddit.com --depth 3
```

### Sortierung nach Typ

Mit der `--sort-by-type` Option werden Dateien automatisch in Typ-spezifische Ordner organisiert:
- Erstellt automatisch Ordner wie PDF/, JPEG/, DOCX/, etc.
- Ähnliche Typen werden zusammengefasst (jpg → JPEG/)
- Dateien ohne Erweiterung → OHNE_ERWEITERUNG/
- Funktioniert mit allen anderen Optionen

Beispiel-Struktur nach Sortierung:
```
Arbeitsordner/
├── PDF/       (alle .pdf Dateien)
├── JPEG/      (alle .jpg und .jpeg Dateien)  
├── PNG/       (alle .png Dateien)
└── DOCX/      (alle .docx Dateien)
```

### Versteckte Dateien einbeziehen

Mit der `--include-hidden` Option werden auch versteckte Dateien (die mit . beginnen) extrahiert:
- Standardmäßig werden versteckte Dateien/Ordner ignoriert
- System-Dateien wie .DS_Store werden weiterhin ignoriert
- Nützlich für Konfigurationsdateien wie .env, .gitignore, etc.

Beispiele:
```bash
# Alle Dateien inklusive versteckte
folder-extractor --include-hidden

# Versteckte Konfigurationsdateien extrahieren
folder-extractor --type json,yml,env --include-hidden
```

### Intelligente Deduplizierung

Mit `--deduplicate` werden Dateien mit identischem Inhalt erkannt und nicht dupliziert:
- Vergleicht Dateien anhand ihres SHA256-Hash
- Gleicher Name + gleicher Inhalt = Quelldatei wird entfernt (kein Duplikat)
- Gleicher Name + anderer Inhalt = Automatische Umbenennung (wie bisher)

Beispiele:
```bash
# Duplikate beim Extrahieren vermeiden
folder-extractor --deduplicate

# Kombiniert mit Sortierung
folder-extractor --sort-by-type --deduplicate
```

### Globale Deduplizierung

Mit `--global-dedup` werden Duplikate im **gesamten Zielordner** erkannt:
- Prüft nicht nur neue Dateien, sondern auch bereits vorhandene
- Findet Duplikate auch wenn Dateinamen unterschiedlich sind
- ⚠️ Kann bei großen Ordnern langsamer sein

```bash
# Globale Prüfung aktivieren
folder-extractor --global-dedup

# Nützlich für Foto-Sammlungen mit vielen Kopien
folder-extractor --type jpg,png --global-dedup
```

### Sicherheitsfeatures

1. **Bestätigung vor Start**: Das Tool zeigt eine detaillierte Vorschau und wartet auf Ihre Bestätigung ("leg los" oder "stop")
2. **ESC zum Abbrechen**: Drücken Sie jederzeit ESC, um den Prozess sicher zu stoppen
3. **Undo-Funktion**: Jede Operation wird gespeichert und kann mit `--undo` rückgängig gemacht werden

## Beispiel

```bash
cd ~/Desktop/MeinProjekt
folder-extractor --depth 2
```

Dies wird:
1. Alle Dateien aus Unterordnern bis zur 2. Ebene finden
2. Diese in den Ordner "MeinProjekt" verschieben
3. Duplikate automatisch umbenennen (z.B. bild.jpg → bild_1.jpg)
4. Alle nun leeren Unterordner entfernen

## Sicherheit

Das Tool verhindert versehentliche Ausführung in Systemordnern. Es läuft ausschließlich in:
- `~/Desktop/*`
- `~/Downloads/*`
- `~/Documents/*`

## Deinstallation

```bash
pip uninstall folder-extractor
```

## Systemanforderungen

- Python 3.7 oder höher
- macOS, Linux oder Windows
- Keine externen Abhängigkeiten

## Lizenz

MIT License