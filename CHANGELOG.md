# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [2.0.0] - 2025-02-04

### 🚀 Hauptfeatures

Diese Version stellt eine signifikante Erweiterung dar mit neuen Betriebsmodi und AI-Integration.

#### **Archive Extraction** (#6)
- Automatisches Entpacken von ZIP-, TAR-, TAR.GZ- und TGZ-Archiven
- Neue Option `--extract-archives` für sichere Archive-Extraktion
- Neue Option `--delete-archives` zum Löschen von Archiven nach erfolgreichem Entpacken
- **Zip Slip Protection**: Schutz gegen Path Traversal Angriffe
  - Validierung aller extrahierten Pfade
  - Ablehnung von absoluten Pfaden in Archives
  - Symlink-Auflösung zur Verhinderung von Escapes
- Deep extraction: Verschachtelte Archive werden rekursiv entpackt
- Unterstützte Formate: ZIP, TAR, TAR.GZ, TGZ
- Integration mit allen existierenden Optionen (Sortierung, Deduplizierung, etc.)

#### **AI-Powered Smart Sorting** (#7, #8, #9)
- **Async Gemini Client** mit retry handling und rate limiting
- **Gemini 3 Flash Preview Model** für schnelle und präzise Kategorisierung
- **Self-Healing Mechanism** mit automatischer Fehlerkorrektur
  - Document Preprocessor für Text-Extraktion
  - Resilience patterns mit exponential backoff
  - Automatische Wiederholung bei API-Fehlern
- **Intelligente Dokumenten-Kategorisierung**:
  - Automatische Erkennung von Kategorie, Sender, Jahr
  - Entity Extraction (Personen, Organisationen, Daten)
  - Template-basierte Pfadgenerierung
- End-to-end Integration Tests für Smart Sorting workflows
- **Anforderung**: Python 3.9+ und `google-generativeai` package

#### **Watch Mode** (#10)
- Neue Option `--watch` für automatische Ordnerüberwachung
- Automatische Verarbeitung neuer Dateien bei Erkennung
- **File Stability Monitoring**: Wartet bis Downloads vollständig sind
  - Konfigurierbare Stabilitätsprüfung
  - Verhindert Verarbeitung unvollständiger Transfers
- Smart debouncing für effiziente Event-Verarbeitung
- Integration mit allen Extraktionsoptionen
- Graceful shutdown mit Ctrl+C
- **Anforderung**: Python 3.9+ und `watchdog` package

#### **Knowledge Graph** (#11)
- **KùzuDB-Integration** für graph-basierte Metadaten-Speicherung
- Document metadata storage mit Entity relationships
- **Natural Language Queries** mit `--ask` Option
  - Beispiel: `folder-extractor --ask "Welche Versicherungsdokumente habe ich?"`
  - Cypher query translation für komplexe Abfragen
- Thread-safe operations mit connection pooling
- Automatisches Schema-Management
- **Anforderung**: Python 3.9+ und `kuzu` package

#### **REST API & WebSocket** (#12)
- **FastAPI-basierte REST API** für native App-Integration
- Neuer Entry Point: `folder-extractor-api`
- **REST Endpoints**:
  - `GET /health` - Health check
  - `POST /api/v1/process` - Einzeldatei verarbeiten
  - `GET /api/v1/zones` - Dropzones auflisten
  - `POST /api/v1/zones` - Dropzone erstellen
  - `DELETE /api/v1/zones/{zone_id}` - Dropzone löschen
  - `POST /api/v1/watcher/start` - Watcher starten
  - `POST /api/v1/watcher/stop` - Watcher stoppen
  - `GET /api/v1/watcher/status` - Watcher-Status abfragen
- **WebSocket Support** (`/ws/chat`):
  - Bidirektionale Kommunikation
  - Real-time Status-Updates
  - Broadcast capabilities
- **Dropzone Management**:
  - Multi-zone Konfiguration
  - Path templates mit Platzhaltern
  - Persistente Speicherung in `~/.config/folder_extractor/zones.json`
- CORS-Konfiguration für localhost
- **Anforderung**: Python 3.9+ und `fastapi`, `uvicorn`, `pydantic>=2.0.0`, `websockets`

### 🎯 Verbesserungen

#### Performance
- Parallele Test-Ausführung mit `pytest-xdist`
- Optimierte Hash-Indexierung für große Ordner
- Connection pooling für Datenbank-Operationen
- Chunked file reading (8KB) für Memory-Effizienz

#### Developer Experience
- **Pyright Integration** für statische Typ-Prüfung
- **LSP Support** für bessere IDE-Integration
- Property-based Tests mit Hypothesis (#4)
- Erweiterte Test-Suite:
  - Unit Tests für alle neuen Module
  - Integration Tests für komplette Workflows
  - Performance Benchmarks
  - Security Tests (Zip Slip, Path Traversal)
- Umfassende Dokumentation:
  - ARCHITECTURE.md mit Dual-Mode Architektur
  - CLAUDE.md mit Python Version Compatibility
  - ANLEITUNG.md mit neuen Features

#### Code Quality
- Path objects statt Strings durchgehend in Tests
- Helper methods extraction für bessere Lesbarkeit
- CodeRabbit und Cubic Review-Vorschläge implementiert
- Ruff linting und formatting durchgehend angewendet

### 🔧 Behoben

- **Undo-Funktion**: Deduplizierte Dateien werden jetzt korrekt wiederhergestellt (#245d4b6)
- **Python 3.8 Kompatibilität**:
  - AI/API Module von Coverage ausgeschlossen auf Python 3.8
  - AI Tests werden auf Python 3.8 übersprungen
  - `from __future__ import annotations` für Kompatibilität
- **CI/CD**: Coverage threshold angepasst, Deep Directory Tests korrigiert
- Diverse Lint-Fehler behoben (E501, B007, F841, SIM108, SIM105)

### 📦 Abhängigkeiten

#### Runtime (CLI Mode - Python 3.8+)
- `rich>=13.0.0` - Enhanced terminal output

#### Optional (API/AI Mode - Python 3.9+)
- `fastapi` - REST API framework
- `uvicorn[standard]` - ASGI server
- `pydantic>=2.0.0` - Data validation
- `websockets` - WebSocket support
- `python-dotenv` - Environment configuration
- `google-generativeai` - Gemini AI client
- `watchdog` - File system monitoring
- `kuzu` - Graph database

#### Development
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `pytest-benchmark>=4.0` - Performance benchmarking
- `pytest-xdist>=3.0` - Parallel test execution
- `hypothesis>=6.0` - Property-based testing

### ⚠️ Breaking Changes

Keine Breaking Changes für CLI-Nutzer. Alle existierenden Befehle funktionieren weiterhin.

**Neue Anforderungen für erweiterte Features:**
- Python 3.9+ erforderlich für AI/API Features (CLI Mode läuft weiterhin auf Python 3.8+)
- Zusätzliche Packages für optionale Features (siehe Abhängigkeiten)

### 🔄 Migration

Keine Migration erforderlich für bestehende CLI-Nutzer.

**Für erweiterte Features:**
```bash
# AI/API Features installieren (Python 3.9+)
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv google-generativeai kuzu watchdog

# API Server starten
folder-extractor-api

# Watch Mode nutzen
folder-extractor --watch --sort-by-type

# Knowledge Graph abfragen
folder-extractor --ask "Welche Rechnungen habe ich?"
```

---

## [1.3.3] - 2025-01-31

### Hinzugefügt
- **Inhaltsbasierte Deduplizierung** mit `--deduplicate` Option
  - Erkennt Dateien mit identischem Inhalt anhand SHA256-Hash
  - Vermeidet echte Duplikate (gleicher Name + gleicher Inhalt)
  - Dateien mit gleichem Namen aber anderem Inhalt werden weiterhin umbenannt
- **Globale Deduplizierung** mit `--global-dedup` Option
  - Prüft gegen ALLE Dateien im Zielordner, nicht nur gleichnamige
  - Findet Duplikate auch bei unterschiedlichen Dateinamen
  - Size-based Pre-filtering für optimale Performance
- `--smart-merge` als Alias für `--deduplicate`
- SHA256-Hashing mit chunked reading (8KB) für große Dateien
- Hash-Index für effiziente globale Duplikat-Erkennung
- Neue Statistik-Kategorien in der Zusammenfassung:
  - "Namens-Duplikate" (umbenannt)
  - "Inhalts-Duplikate" (übersprungen)
  - "Globale Duplikate" (im Zielordner gefunden)

### Geändert
- History-Dateien werden jetzt zentral gespeichert:
  - macOS/Linux: `~/.config/folder_extractor/history/`
  - Windows: `%APPDATA%/folder_extractor/history/`
- Automatische Migration von lokalen History-Dateien
- Immutable-Flag für History-Dateien auf macOS (Schutz vor versehentlichem Löschen)

### Behoben
- Kritischer Bug behoben: Versteckte Dateien in Unterordnern wurden fälschlicherweise extrahiert, auch wenn `--include-hidden` nicht gesetzt war
- Die Logik für das Durchsuchen von Unterordnern wurde korrigiert, sodass versteckte Dateien nur mit dem expliziten Flag extrahiert werden

### Intern
- Modulare Architektur mit klarer Trennung (CLI, Core, Config, Utils)
- Dependency Injection für bessere Testbarkeit
- Thread-safe State Management
- Property-based Tests mit Hypothesis
- Ruff Linter und Formatter integriert
- 95%+ Test-Coverage

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
