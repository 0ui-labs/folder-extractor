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

- Python 3.8 oder höher
- macOS, Linux oder Windows
- **CLI-Modus**: Nur `rich` als externe Abhängigkeit
- **API-Modus**: `fastapi`, `uvicorn`, `pydantic` (optional)

## Lizenz

MIT License

## API Server (für macOS Integration)

Folder Extractor bietet eine REST-API und WebSocket-Schnittstelle für die Integration mit nativen macOS-Apps (z.B. Swift-Apps).

### API-Dependencies installieren

```bash
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv
```

### Server starten

```bash
# Standard: localhost:23456
python run_api.py

# Eigener Port
python run_api.py --port 8000

# Development-Mode mit Auto-Reload
python run_api.py --reload

# Alle Optionen
python run_api.py --host 127.0.0.1 --port 23456 --log-level debug --reload
```

Nach dem Start ist die API verfügbar unter:
- **API Endpunkte:** `http://localhost:23456`
- **Interaktive Dokumentation:** `http://localhost:23456/docs`
- **Alternative Docs:** `http://localhost:23456/redoc`

### Verfügbare Endpunkte

#### Health Check
- `GET /health` - Server-Status prüfen

#### Dateiverarbeitung
- `POST /api/v1/process` - Einzelne Datei verarbeiten
  ```json
  {
    "filepath": "/Users/username/Desktop/document.pdf"
  }
  ```

#### Dropzone-Verwaltung
- `GET /api/v1/zones` - Alle konfigurierten Dropzones abrufen
- `POST /api/v1/zones` - Neue Dropzone erstellen
  ```json
  {
    "name": "Dokumente",
    "path": "/Users/username/Desktop/Dropzone",
    "enabled": true,
    "auto_sort": true,
    "categories": ["Finanzen", "Verträge"]
  }
  ```
- `DELETE /api/v1/zones/{zone_id}` - Dropzone löschen

#### Watch-Mode
- `POST /api/v1/watcher/start` - Überwachung für eine Zone starten
  ```json
  {
    "zone_id": "uuid-here"
  }
  ```
- `POST /api/v1/watcher/stop` - Überwachung stoppen
  ```json
  {
    "zone_id": "uuid-here"
  }
  ```
- `GET /api/v1/watcher/status` - Status aller Watcher abrufen

#### WebSocket (Echtzeit-Kommunikation)
- `WS /ws/chat` - Bidirektionale Kommunikation für Chat und Status-Updates
  ```javascript
  // Beispiel: JavaScript WebSocket Client
  const ws = new WebSocket('ws://localhost:23456/ws/chat');
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log(message.type, message.data);
  };
  ```

### Konfiguration

Erstelle eine `.env`-Datei im Projektverzeichnis (basierend auf `.env.example`):

```bash
cp .env.example .env
```

Passe die API-Konfiguration an:
```
API_PORT=23456
API_HOST=127.0.0.1
API_LOG_LEVEL=info
```

### Sicherheitshinweise

⚠️ **Wichtig für die Produktion:**
- Der API-Server läuft standardmäßig nur auf `localhost` (127.0.0.1)
- Für externe Verbindungen `API_HOST=0.0.0.0` setzen (nicht empfohlen ohne zusätzliche Sicherheitsmaßnahmen)
- CORS ist standardmäßig für `localhost` konfiguriert
- Für Produktionsumgebungen zusätzliche Authentifizierung implementieren

### Integration mit Swift (macOS App)

Beispiel für HTTP-Request in Swift:

```swift
import Foundation

// Datei verarbeiten
let url = URL(string: "http://localhost:23456/api/v1/process")!
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")

let body: [String: Any] = ["filepath": "/Users/username/Desktop/document.pdf"]
request.httpBody = try? JSONSerialization.data(withJSONObject: body)

URLSession.shared.dataTask(with: request) { data, response, error in
    // Handle response
}.resume()
```

Beispiel für WebSocket in Swift:

```swift
import Foundation

let url = URL(string: "ws://localhost:23456/ws/chat")!
let webSocket = URLSession.shared.webSocketTask(with: url)
webSocket.resume()

// Nachricht empfangen
webSocket.receive { result in
    switch result {
    case .success(let message):
        // Handle message
    case .failure(let error):
        print("WebSocket error: \(error)")
    }
}
```

**Hinweis:** Die API ist optional und wird nur für die native macOS-App benötigt. Die CLI-Funktionalität bleibt unverändert.