# Geplante Features

---

## Nächste Prioritäten (v1.4.0)

Diese zwei Features sind als nächstes geplant, da sie bestehende Probleme lösen:

### Feature A: Persistente Konfiguration

**Status:** Geplant

**Problem:**
Häufig genutzte Optionen müssen bei jedem Aufruf neu eingegeben werden:
```bash
# Jedes Mal tippen:
folder-extractor --deduplicate --sort-by-type --global-dedup
```

**Lösung:**
Eine Konfigurationsdatei, die automatisch geladen wird:
```bash
# Einmalig konfigurieren:
folder-extractor --save-config --deduplicate --sort-by-type

# Danach reicht:
folder-extractor
# → Lädt automatisch gespeicherte Einstellungen
```

**Technische Details:**

| Aspekt | Details |
|--------|---------|
| Speicherort (macOS/Linux) | `~/.config/folder_extractor/config.json` |
| Speicherort (Windows) | `%APPDATA%/folder_extractor/config.json` |
| Priorität | CLI-Argumente > Konfigurationsdatei > Standardwerte |

**Neue CLI-Optionen:**
```bash
--save-config       # Aktuelle Optionen als Standard speichern
--show-config       # Gespeicherte Konfiguration anzeigen
--reset-config      # Konfiguration auf Standard zurücksetzen
--no-config         # Gespeicherte Konfiguration ignorieren
```

**Betroffene Dateien:**
- `folder_extractor/cli/parser.py` – Neue Argumente
- `folder_extractor/cli/app.py` – Konfiguration laden
- `folder_extractor/config/settings.py` – Bereits vorhanden: `save_to_file()`, `load_from_file()`

---

### Feature B: Undo für Duplikate (Bugfix)

**Status:** Bugfix erforderlich

**Problem:**
Bei `--deduplicate` werden Quelldateien mit identischem Inhalt **gelöscht**:

```python
# file_operations.py, Zeile 801
source_path.unlink()  # Datei wird gelöscht!
```

Die History speichert zwar `content_duplicate: True`, aber beim Undo kann die Datei nicht wiederhergestellt werden!

**Beispiel des Bugs:**
```
Vorher:
📁 Ordner1/foto.jpg (Original)
📁 Ordner2/foto.jpg (Identische Kopie)

Nach folder-extractor --deduplicate:
📄 foto.jpg (aus Ordner1)
❌ Ordner2/foto.jpg wurde GELÖSCHT

Nach folder-extractor --undo:
📁 Ordner1/foto.jpg (wiederhergestellt)
❌ Ordner2/foto.jpg FEHLT IMMER NOCH!  ← BUG
```

**Lösung:**
Beim Undo soll die verbleibende Datei **kopiert** werden:

```
Nach folder-extractor --undo (FIXED):
📁 Ordner1/foto.jpg (zurück verschoben)
📁 Ordner2/foto.jpg (kopiert aus Zielordner)  ✓
```

**Technische Änderungen:**

1. **History erweitern:**
```json
{
  "original_pfad": "/Ordner2/foto.jpg",
  "neuer_pfad": "/Ziel/foto.jpg",
  "content_duplicate": true,
  "duplicate_of": "/Ziel/foto.jpg"  // NEU: Referenz zur verbleibenden Datei
}
```

2. **Undo-Logik anpassen:**
```python
if entry.get("content_duplicate"):
    # KOPIEREN statt verschieben
    shutil.copy2(duplicate_source, original_path)
else:
    self.file_operations.move_file(new_path, original_path)
```

**Betroffene Dateien:**
- `folder_extractor/core/file_operations.py` – History-Einträge erweitern
- `folder_extractor/core/extractor.py` – Undo-Logik anpassen

---

### Zusammenfassung v1.4.0

| Feature | Typ | Aufwand | Status |
|---------|-----|---------|--------|
| Persistente Konfiguration | Neu | Mittel | Geplant |
| Undo für Duplikate | Bugfix | Mittel | Offen |

---

## Technische Verbesserungen (v1.5.0)

### Erweiterter Dry-Run (Diff-View)

**Status:** Geplant

**Aktuell:** Zeigt an, was passieren würde.

**Verbesserung:** Eine tabellarische Ansicht mit klaren Aktions-Tags:
```
[MOVE]   subdir/doc.pdf      -> ./doc.pdf
[RENAME] subdir/image.jpg    -> ./image_1.jpg (Namenskonflikt)
[SKIP]   subdir/foto.jpg     -> (Duplikat von ./foto.jpg)
[SKIP]   subdir/.DS_Store    -> (Systemdatei)
```

**Vorteile:**
- Bessere Übersicht über geplante Aktionen
- Klare Unterscheidung: Move vs. Rename vs. Skip
- Grund für Skip wird angezeigt

---

### Logging-System

**Status:** Geplant

**Problem:** Aktuell nur `print()` Ausgaben - keine persistente Protokollierung.

**Lösung:** Nutzung des Python `logging` Moduls mit optionaler Datei-Ausgabe.

**Neue CLI-Option:**
```bash
folder-extractor --log-file operation.log
```

**Vorteile:**
- Nachvollziehbarkeit bei Fehlern
- Debug-Informationen ohne Konsolen-Flut
- Log-Rotation für große Operationen

---

### Internationalisierung (i18n)

**Status:** Geplant

**Problem:** Der Code vermischt englische Variablennamen mit deutschen Ausgabetexten.

**Lösung:** Nutzung des `gettext` Moduls (Standard Library) oder eine einfache JSON-Lookup-Table für Strings.

**Struktur:**
```
folder_extractor/
└── locales/
    ├── de/messages.json
    └── en/messages.json
```

**Vorteile:**
- Englisch als Default (internationaler Standard)
- Deutsch optional (`--lang de`)
- Einfache Erweiterung für weitere Sprachen

---

## Distribution (v1.5.0+)

### Standalone Binaries

**Status:** Geplant

**Problem:** Nicht jeder Nutzer hat Python installiert oder weiß, wie man `pip` benutzt.

**Lösung:** Automatische Binary-Erstellung via GitHub Actions:

| Platform | Tool | Output |
|----------|------|--------|
| Windows | PyInstaller | `folder-extractor.exe` |
| macOS | PyInstaller | `folder-extractor` (Universal Binary) |
| Linux | PyInstaller | `folder-extractor` (AppImage) |

**GitHub Actions Workflow:**
```yaml
- name: Build Executables
  run: |
    pip install pyinstaller
    pyinstaller --onefile folder_extractor/main.py
```

**Impact:** Massiv erhöhte Nutzerbasis - Download & Doppelklick statt pip install.

---

### Homebrew Tap (macOS)

**Status:** Geplant

**Für Mac-Nutzer ist `brew install` der Goldstandard.**

**Setup:**
1. Erstelle Repository: `github.com/0ui-labs/homebrew-tap`
2. Erstelle Formula: `folder-extractor.rb`

**Installation für Nutzer:**
```bash
brew tap 0ui-labs/tap
brew install folder-extractor
```

---

## Langfristige Vision

### 1. Smart Content Intelligence

**Inhaltsbasierte Deduplizierung** - ✅ Bereits umgesetzt (v1.3.3)

**Semantische Sortierung (geplant):**
- Sortierung nach **Thema** statt nur Dateityp
- Keyword-Analyse oder lokale NLP
- Ergebnis: `Rechnung_Telekom.pdf` → `Finanzen/`

---

### 2. Deep Extraction (Archiv-Handling)

**Transparente Archiv-Entpackung:**
- ZIP, 7Z, TAR, RAR wie Ordner behandeln
- Verschachtelte Archive automatisch entpacken
- Optional: Archiv nach Extraktion löschen

---

### 3. Watch Mode (Workflow Automation)

**Der "Hausmeister"-Modus:**
```bash
folder-extractor --watch ~/Downloads
```
- Daemon-Prozess überwacht Ordner
- Neue Dateien werden automatisch sortiert
- "Zero Inbox" für Downloads

---

### 4. Timeline Organization (Medien)

**EXIF & Metadaten-Sortierung:**
```bash
folder-extractor --sort-by-date --format "{year}/{month}"
```
- Sortierung nach Aufnahmedatum (nicht Änderungsdatum)
- Perfekt für Foto-Sammlungen
- Struktur: `2024/01/`, `2024/02/`

---

### 5. TUI (Terminal User Interface)

**Interaktives Dashboard mit `Textual` oder `Rich`:**
- Links: Dateibaum (Vorher)
- Rechts: Dateibaum (Nachher Vorschau)
- Unten: Live-Log und Progress-Bar
- Einzelne Dateien mit Leertaste ausschließen

---

### 6. Plugin-System / Hooks

**Pre-Move / Post-Move Hooks:**
```python
# hooks/compress_images.py
def post_move(file_path):
    if file_path.suffix == '.png':
        compress_with_tinypng(file_path)
```

---

### 7. Multi-Threaded Processing

**Parallele Verarbeitung für große Dateimengen:**
- Thread-Pool für Hash-Berechnung
- Paralleles Verschieben (falls unterschiedliche Zielordner)
- Deutlich schneller bei 1000+ Dateien

---

## Roadmap Übersicht

| Version | Features | Status |
|---------|----------|--------|
| **v1.3.3** | SHA256 Dedup, Global Dedup | ✅ Released |
| **v1.4.0** | Persistente Config, Undo-Bugfix | 🟡 Geplant |
| **v1.5.0** | Logging, i18n, Dry-Run++, Binaries | 📋 Backlog |
| **v2.0.0** | Watch Mode, Archive Support, TUI | 🔮 Vision |

---

**Repository**: https://github.com/0ui-labs/folder-extractor
