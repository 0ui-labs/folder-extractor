# Folder Extractor

Ein intelligentes Tool zum Extrahieren und Organisieren von Dateien aus verschachtelten Ordnerstrukturen. Von einfachen CLI-Operationen bis hin zu AI-gestützter Dokumentenverwaltung.

**Version 2.0.0** | [CHANGELOG](CHANGELOG.md) | [Anleitung](ANLEITUNG.md) | [Architektur](ARCHITECTURE.md)

## ✨ Highlights

- 🤖 **AI-Powered Smart Sorting**: Automatische Dokumentenkategorisierung mit Google Gemini
- 📦 **Archive Extraction**: Sicheres Entpacken von ZIP/TAR mit Zip Slip Protection
- 👁️ **Watch Mode**: Automatische Verarbeitung bei neuen Dateien
- 🧠 **Knowledge Graph**: Natürlichsprachige Abfragen deiner Dokumente
- 🌐 **REST API**: Integration mit nativen macOS/iOS Apps
- 🔒 **Security First**: Path validation, Zip Slip protection, sichere Operationen

## 🚀 Features

### Core Features (Python 3.8+)
- 🔒 **Sicherheitsprüfung**: Läuft nur in Desktop, Downloads oder Documents Ordnern
- 📁 **Intelligente Duplikat-Behandlung**: Content-basierte Deduplizierung mit SHA256
- 🎯 **Flexible Tiefensteuerung**: Bestimmen Sie, wie tief in die Ordnerstruktur gesucht werden soll
- 🗂️ **Sortierung nach Typ**: Organisiere Dateien automatisch in Typ-Ordner (PDF/, JPEG/, etc.)
- 📎 **Dateityp-Filter**: Extrahiere nur bestimmte Dateitypen (pdf, jpg, mp3, etc.)
- 🌐 **Domain-Filter**: Filtere Web-Links nach bestimmten Domains
- 📦 **Archive Extraction**: Entpackt ZIP, TAR, TAR.GZ, TGZ sicher
- 🔄 **Intelligente Deduplizierung**: Erkennt identische Dateien anhand des Inhalts
- 🌍 **Globale Deduplizierung**: Findet Duplikate im gesamten Zielordner
- 👻 **Versteckte Dateien**: Optional auch versteckte Dateien einbeziehen
- 🧹 **Automatisches Aufräumen**: Entfernt leere Ordner nach dem Verschieben
- ↩️ **Undo-Funktion**: Macht die letzte Operation rückgängig
- 🔍 **Dry-Run Modus**: Zeigt was passieren würde, ohne es zu tun
- 📈 **Fortschrittsanzeige**: Real-time Progress mit Rich Terminal Output

### Erweiterte Features (Python 3.9+)
- 🤖 **AI-Powered Smart Sorting**: Gemini-basierte Dokumentenkategorisierung
  - Automatische Erkennung: Kategorie, Sender, Jahr, Entities
  - Template-basierte Pfadgenerierung
  - Self-healing mechanism mit Fehlerkorrektur
- 👁️ **Watch Mode**: Automatische Ordnerüberwachung
  - File stability monitoring (wartet bis Downloads fertig)
  - Smart debouncing für effiziente Verarbeitung
  - Integration mit AI-Kategorisierung
- 🧠 **Knowledge Graph**: KùzuDB-basierte Metadaten-Speicherung
  - Natural Language Queries: `folder-extractor --ask "Welche Rechnungen von Apple?"`
  - Entity relationships und Dokumenten-Kontext
  - Cypher query translation
- 🌐 **REST API & WebSocket**: FastAPI-basiert für native Apps
  - 8 REST Endpoints für Dateiverarbeitung und Zones
  - WebSocket für Real-time Updates
  - Dropzone Management mit Templates

## 📦 Installation

### Basis-Installation (CLI Mode - Python 3.8+)

```bash
# Standard-Installation
pip install .

# Für Entwicklung (editierbar)
pip install -e .

# Mit Test-Dependencies
pip install -e ".[test]"
```

### Erweiterte Features (Python 3.9+)

```bash
# AI/API Features
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv google-generativeai kuzu watchdog

# Oder nur spezifische Features
pip install google-generativeai kuzu  # AI + Knowledge Graph
pip install watchdog                   # Watch Mode
pip install fastapi uvicorn[standard]  # REST API
```

Nach der Installation:
- `folder-extractor` - CLI Tool (verfügbar systemweit)
- `folder-extractor-api` - API Server (nur mit API-Dependencies)

## 🎯 Schnellstart

### Grundlegende Verwendung

```bash
# Alle Dateien aus Unterordnern extrahieren
cd ~/Downloads/MeinOrdner
folder-extractor

# Testlauf (zeigt nur was passieren würde)
folder-extractor --dry-run

# Nach Dateityp sortieren
folder-extractor --sort-by-type

# Nur bestimmte Dateitypen
folder-extractor --type pdf,jpg,png

# Duplikate vermeiden
folder-extractor --deduplicate --global-dedup
```

### Archive Extraction

```bash
# Archive entpacken
folder-extractor --extract-archives

# Archive entpacken und Originale löschen
folder-extractor --extract-archives --delete-archives

# Archive entpacken und nach Typ sortieren
folder-extractor --extract-archives --sort-by-type
```

### Watch Mode (Python 3.9+)

```bash
# Ordner automatisch überwachen
folder-extractor --watch --sort-by-type

# Mit Archive-Extraction
folder-extractor --watch --extract-archives --delete-archives

# Mit Ctrl+C beenden
```

### Knowledge Graph Abfragen (Python 3.9+)

```bash
# Natürlichsprachige Abfragen
folder-extractor --ask "Welche Versicherungsdokumente habe ich?"
folder-extractor --ask "Zeig mir Rechnungen von Apple aus 2024"
folder-extractor --ask "Welche Verträge laufen aus?"
```

## 📚 Verwendung

### Dateityp-Filter

Extrahiere nur bestimmte Dateitypen:

```bash
# Nur PDFs
folder-extractor --type pdf

# Mehrere Typen
folder-extractor --type pdf,doc,docx,txt

# Nur Bilder aus 2 Ebenen
folder-extractor --type jpg,jpeg,png,heic --depth 2

# Nur Videos
folder-extractor --type mp4,avi,mkv,mov
```

**Unterstützte Typen**: pdf, doc, docx, txt, jpg, jpeg, png, gif, mp4, mp3, wav, json, xml, csv, py, js, java, cpp, html, css, url, webloc, und viele mehr.

### Domain-Filter für Web-Links

Filtere Browser-Lesezeichen nach Domains:

```bash
# Nur YouTube-Links
folder-extractor --type url,webloc --domain youtube.com

# Mehrere Domains
folder-extractor --type url --domain github.com,stackoverflow.com,reddit.com

# Mit Subdomains (youtube.com matched auch m.youtube.com)
folder-extractor --type url,webloc --domain youtube.com --depth 3
```

### Sortierung nach Typ

Organisiere Dateien automatisch in Typ-spezifische Ordner:

```bash
# Automatisch sortieren
folder-extractor --sort-by-type

# Kombiniert mit anderen Optionen
folder-extractor --sort-by-type --deduplicate
folder-extractor --sort-by-type --extract-archives
```

**Ergebnis:**
```
Downloads/
├── PDF/       (alle .pdf Dateien)
├── JPEG/      (alle .jpg und .jpeg Dateien)
├── PNG/       (alle .png Dateien)
├── VIDEO/     (alle .mp4, .avi, .mkv Dateien)
└── DOCX/      (alle .docx Dateien)
```

### Intelligente Deduplizierung

Vermeide Duplikate basierend auf Dateiinhalt:

```bash
# Content-basierte Deduplizierung
folder-extractor --deduplicate

# Globale Deduplizierung (prüft gesamten Zielordner)
folder-extractor --global-dedup

# Kombiniert mit Sortierung
folder-extractor --sort-by-type --deduplicate --global-dedup
```

**Was passiert:**
- `--deduplicate`: Dateien mit gleichem Namen + gleichem Inhalt werden übersprungen
- `--global-dedup`: Findet Duplikate auch bei unterschiedlichen Dateinamen
- Hash-Vergleich: SHA256 mit size-based pre-filtering für Performance

### Versteckte Dateien

Beziehe versteckte Dateien (beginnend mit `.`) ein:

```bash
# Alle Dateien inklusive versteckte
folder-extractor --include-hidden

# Versteckte Konfigurationsdateien
folder-extractor --type json,yml,env --include-hidden
```

**Hinweis:** System-Dateien wie `.DS_Store` werden weiterhin ignoriert.

### Undo-Funktion

Mache die letzte Operation rückgängig:

```bash
# Letzte Operation rückgängig machen
folder-extractor --undo
```

Jede Operation wird in `~/.config/folder_extractor/history/` gespeichert und kann vollständig wiederhergestellt werden.

## 🔐 Sicherheit

### Sichere Ordner

Das Tool läuft **nur** in diesen Ordnern:
- `~/Desktop/*`
- `~/Downloads/*`
- `~/Documents/*`

Dies verhindert versehentliche Ausführung in Systemordnern.

### Archive Security (Zip Slip Protection)

Bei `--extract-archives`:
- ✅ Alle extrahierten Pfade werden validiert
- ✅ Absolute Pfade in Archives werden abgelehnt
- ✅ Path Traversal Angriffe (`../../../etc/passwd`) werden blockiert
- ✅ Symlink-Auflösung zur Verhinderung von Escapes

**Unterstützte Formate:** ZIP, TAR, TAR.GZ, TGZ

## 🌐 REST API Server (Python 3.9+)

### Installation

```bash
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv
```

### Server starten

```bash
# Standard: localhost:23456
folder-extractor-api

# Eigener Port
folder-extractor-api --port 8000

# Development Mode mit Auto-Reload
folder-extractor-api --reload

# Alle Optionen
folder-extractor-api --host 127.0.0.1 --port 23456 --log-level debug --reload
```

Nach dem Start verfügbar unter:
- **API Docs:** `http://localhost:23456/docs` (interaktiv)
- **Alternative Docs:** `http://localhost:23456/redoc`

### Verfügbare Endpunkte

#### Health & Status
- `GET /health` - Server-Status prüfen

#### Dateiverarbeitung
- `POST /api/v1/process` - Einzelne Datei verarbeiten

#### Dropzone-Verwaltung
- `GET /api/v1/zones` - Alle Dropzones auflisten
- `POST /api/v1/zones` - Neue Dropzone erstellen
- `DELETE /api/v1/zones/{zone_id}` - Dropzone löschen

#### Watch Mode (API)
- `POST /api/v1/watcher/start` - Watcher für Zone starten
- `POST /api/v1/watcher/stop` - Watcher stoppen
- `GET /api/v1/watcher/status` - Status aller Watcher

#### WebSocket
- `WS /ws/chat` - Bidirektionale Kommunikation für Real-time Updates

### Beispiel-Request

```bash
# Health Check
curl http://localhost:23456/health

# Datei verarbeiten
curl -X POST http://localhost:23456/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/Users/username/Desktop/document.pdf"}'

# Dropzone erstellen
curl -X POST http://localhost:23456/api/v1/zones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dokumente",
    "path": "/Users/username/Desktop/Dropzone",
    "enabled": true,
    "auto_sort": true,
    "categories": ["Finanzen", "Verträge"]
  }'
```

### WebSocket-Beispiel (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:23456/ws/chat');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Type:', message.type);
  console.log('Data:', message.data);
};

ws.send(JSON.stringify({
  type: 'query',
  data: { question: 'Welche PDFs habe ich?' }
}));
```

### Swift Integration (macOS/iOS)

```swift
import Foundation

// HTTP Request
let url = URL(string: "http://localhost:23456/api/v1/process")!
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")

let body: [String: Any] = ["filepath": "/Users/username/Desktop/document.pdf"]
request.httpBody = try? JSONSerialization.data(withJSONObject: body)

URLSession.shared.dataTask(with: request) { data, response, error in
    // Handle response
}.resume()

// WebSocket
let wsURL = URL(string: "ws://localhost:23456/ws/chat")!
let webSocket = URLSession.shared.webSocketTask(with: wsURL)
webSocket.resume()

webSocket.receive { result in
    switch result {
    case .success(let message):
        // Handle message
    case .failure(let error):
        print("Error: \(error)")
    }
}
```

### Konfiguration

Erstelle `.env` Datei:

```bash
API_PORT=23456
API_HOST=127.0.0.1
API_LOG_LEVEL=info
GEMINI_API_KEY=your-api-key-here
```

### Sicherheitshinweise

⚠️ **Wichtig für Produktion:**
- Server läuft standardmäßig nur auf `localhost` (127.0.0.1)
- Für externe Verbindungen: `API_HOST=0.0.0.0` (nicht empfohlen ohne Auth)
- CORS ist für `localhost` konfiguriert
- Für Produktionsumgebungen: Authentifizierung implementieren

## 📖 Dokumentation

- **[ANLEITUNG.md](ANLEITUNG.md)** - Ausführliche Bedienungsanleitung auf Deutsch
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architektur-Dokumentation und Design Patterns
- **[CHANGELOG.md](CHANGELOG.md)** - Versionshistorie und Änderungen
- **[CLAUDE.md](CLAUDE.md)** - Entwickler-Anleitung für Claude Code

## 💻 Systemanforderungen

### Basis (CLI Mode)
- **Python**: 3.8 oder höher
- **Betriebssysteme**: macOS, Linux, Windows
- **Runtime Dependencies**: `rich>=13.0.0`

### Erweiterte Features
- **Python**: 3.9 oder höher (für AI/API Features)
- **Optionale Dependencies**:
  - `google-generativeai` - AI Smart Sorting
  - `kuzu` - Knowledge Graph
  - `watchdog` - Watch Mode
  - `fastapi`, `uvicorn`, `pydantic`, `websockets` - REST API

## 🔄 Beispiel-Workflows

### 1. Downloads aufräumen

```bash
cd ~/Downloads
folder-extractor --dry-run --sort-by-type  # Erst testen
folder-extractor --sort-by-type --deduplicate  # Dann ausführen
```

### 2. Foto-Sammlung konsolidieren

```bash
cd ~/Pictures/Urlaub
folder-extractor --type jpg,jpeg,png,heic --deduplicate --global-dedup
```

### 3. Backup-Archive organisieren

```bash
cd ~/Documents/Backups
folder-extractor --extract-archives --sort-by-type
# Originale bleiben erhalten, ODER:
folder-extractor --extract-archives --delete-archives --sort-by-type
```

### 4. Download-Ordner automatisch organisieren

```bash
cd ~/Downloads
folder-extractor --watch --sort-by-type --extract-archives
# Läuft kontinuierlich, Ctrl+C zum Beenden
```

### 5. Dokumente mit AI organisieren (Python 3.9+)

```bash
# API-Key konfigurieren
export GEMINI_API_KEY=your-key

# Automatische Kategorisierung
cd ~/Documents/Inbox
folder-extractor --watch --sort-by-type

# Später abfragen
folder-extractor --ask "Welche Versicherungsdokumente habe ich aus 2024?"
```

## 🤝 Beitragen

Beiträge sind willkommen! Siehe [ARCHITECTURE.md](ARCHITECTURE.md) für Details zur Codebase-Struktur.

**Entwicklung:**
```bash
# Installation mit Test-Dependencies
pip install -e ".[test]"

# Tests ausführen
python run_tests.py

# Mit Coverage
python run_tests.py coverage

# Linting & Formatting
ruff check .
ruff format .

# Type Checking
pyright
```

## 📄 Lizenz

MIT License - siehe LICENSE-Datei für Details.

## 🙏 Credits

- Entwickelt von **Philipp Briese**
- AI-Integration: Google Gemini 3 Flash Preview
- Graph Database: KùzuDB
- Terminal UI: Rich Library
- Web Framework: FastAPI

---

**Viel Erfolg beim Aufräumen!** 🗂️

Für Fragen und Issues: `folder-extractor --help` oder [GitHub Issues](https://github.com/0ui-labs/folder-extractor/issues)
