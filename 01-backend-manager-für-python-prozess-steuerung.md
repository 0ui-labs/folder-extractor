I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Beobachtungen

Das Projekt ist ein Python-basiertes Dateiextraktions-Tool mit FastAPI-Server (`file:run_api.py`), der standardmäßig auf `localhost:23456` läuft. Der Server bietet einen `/health` Endpoint für Status-Checks und unterstützt WebSocket-Kommunikation. Die Konfiguration erfolgt über `.env` Datei mit Variablen wie `API_PORT`, `API_HOST` und `API_LOG_LEVEL`. Es existiert noch kein Swift-Code im Projekt, daher wird eine neue Struktur aufgebaut.

## Ansatz

Der `BackendManager` wird als Singleton-Klasse implementiert, die den Python-Prozess über `Process` (NSTask) verwaltet. Die Pfad-Erkennung erfolgt über Bundle-relative Pfade mit Fallback-Strategien für Development und Production. Stdout/Stderr werden über Pipes erfasst und an ein Logging-System weitergeleitet. Der Prozess wird beim App-Beenden über `terminate()` sauber gestoppt, mit zusätzlichem `SIGKILL` als Fallback nach Timeout.

## Implementierungsschritte

### 1. Dateistruktur erstellen

Erstelle das Verzeichnis `swift/` im Projekt-Root und darin die Datei `BackendManager.swift`.

### 2. BackendManager Klasse-Grundgerüst

Implementiere eine `BackendManager` Klasse mit folgenden Eigenschaften:

**Singleton-Pattern:**
- `shared` als statische Instanz für globalen Zugriff
- Private Initialisierung

**Properties:**
- `process: Process?` - Der Python-Prozess
- `isRunning: Bool` - Status-Flag
- `outputPipe: Pipe` - Für stdout
- `errorPipe: Pipe` - Für stderr
- `logHandler: ((String, LogLevel) -> Void)?` - Callback für Logs

**Enums:**
- `LogLevel` mit Cases: `.info`, `.warning`, `.error`, `.debug`
- `BackendError` mit Cases: `.pythonNotFound`, `.scriptNotFound`, `.startupFailed`, `.alreadyRunning`

### 3. Pfad-Erkennungslogik implementieren

**Methode `findPythonInterpreter() -> URL?`:**
- Prüfe Bundle-relative Pfade: `Resources/venv/bin/python3`, `Resources/.venv/bin/python3`
- Prüfe Projekt-relative Pfade für Development: `../venv/bin/python3`, `../.venv/bin/python3`
- Fallback auf System-Python: `/usr/bin/python3`, `/usr/local/bin/python3`
- Validiere Existenz mit `FileManager.default.fileExists(atPath:)`

**Methode `findRunAPIScript() -> URL?`:**
- Prüfe Bundle-relative Pfade: `Resources/run_api.py`
- Prüfe Projekt-relative Pfade: `../run_api.py`, `../../run_api.py`
- Nutze `Bundle.main.resourceURL` als Basis
- Validiere Lesbarkeit der Datei

### 4. Process-Start-Logik

**Methode `startBackend() throws`:**

**Validierung:**
- Prüfe ob bereits läuft (`isRunning == true`)
- Finde Python-Interpreter, werfe `.pythonNotFound` bei Fehler
- Finde run_api.py Script, werfe `.scriptNotFound` bei Fehler

**Process-Konfiguration:**
- Erstelle `Process()` Instanz
- Setze `executableURL` auf Python-Interpreter
- Setze `arguments`: `[scriptPath, "--host", "127.0.0.1", "--port", "23456"]`
- Setze `currentDirectoryURL` auf Projekt-Root (Parent von run_api.py)

**Environment-Variablen:**
- Kopiere System-Environment: `ProcessInfo.processInfo.environment`
- Füge hinzu: `PYTHONUNBUFFERED=1`
- Optional: `API_HOST=127.0.0.1`, `API_PORT=23456`, `API_LOG_LEVEL=info`

**Pipes einrichten:**
- Erstelle `Pipe()` für stdout und stderr
- Setze `process.standardOutput = outputPipe`
- Setze `process.standardError = errorPipe`
- Registriere `NotificationCenter` Observer für `FileHandle.readCompletionNotification`

**Process starten:**
- Rufe `process.run()` auf (kann werfen)
- Setze `isRunning = true`
- Starte asynchrones Lesen der Pipes

### 5. Logging-System

**Methode `setupPipeReading()`:**
- Nutze `readabilityHandler` auf `FileHandle` für moderne Async-Reads
- Für stdout: Parse Zeilen und rufe `logHandler?(.info, line)` auf
- Für stderr: Parse Zeilen und rufe `logHandler?(.error, line)` auf
- Erkenne spezielle Muster:
  - "ERROR" → `.error`
  - "WARNING" → `.warning`
  - "INFO" → `.info`
  - "Starting Folder Extractor API" → Startup erkannt

**Methode `parseLogLine(_ line: String) -> (LogLevel, String)`:**
- Extrahiere Log-Level aus Python-Logging-Format
- Format: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`
- Returniere Tuple mit Level und bereinigter Message

### 6. Process-Überwachung

**Methode `monitorProcess()`:**
- Nutze `process.terminationHandler` Callback
- Bei Termination: Setze `isRunning = false`
- Logge Exit-Code: `process.terminationStatus`
- Bei unerwartetem Exit: Rufe `logHandler?(.error, "Backend crashed")` auf

**Property `terminationStatus: Int32?`:**
- Speichere letzten Exit-Code für Debugging

### 7. Sauberes Beenden

**Methode `stopBackend()`:**

**Graceful Shutdown:**
- Prüfe ob `process` existiert und läuft
- Sende `SIGTERM`: `process.terminate()`
- Warte max. 5 Sekunden: `DispatchQueue.global().asyncAfter(deadline: .now() + 5)`

**Force Kill als Fallback:**
- Wenn nach 5 Sekunden noch läuft: `process.interrupt()` (SIGKILL)
- Logge Warnung bei Force-Kill

**Cleanup:**
- Schließe Pipes: `outputPipe.fileHandleForReading.closeFile()`
- Setze `isRunning = false`
- Setze `process = nil`

**Methode `deinit`:**
- Rufe `stopBackend()` auf für automatisches Cleanup

### 8. Helper-Methoden

**Methode `isServerReachable() async -> Bool`:**
- Sende HTTP GET zu `http://127.0.0.1:23456/health`
- Nutze `URLSession.shared.data(from:)`
- Returniere `true` bei Status 200, sonst `false`
- Timeout: 2 Sekunden

**Methode `waitForServerReady(timeout: TimeInterval) async throws`:**
- Polling-Loop mit `isServerReachable()`
- Prüfe alle 0.5 Sekunden
- Werfe Timeout-Error nach `timeout` Sekunden
- Nutze `Task.sleep(nanoseconds:)` für Delays

### 9. Error Handling

**Alle Methoden mit `throws`:**
- Nutze `BackendError` enum für spezifische Fehler
- Logge alle Errors über `logHandler`
- Gebe aussagekräftige Error-Messages

**Beispiel Error-Messages:**
- `.pythonNotFound`: "Python interpreter not found. Please ensure venv is set up."
- `.scriptNotFound`: "run_api.py not found. Check bundle resources."
- `.startupFailed`: "Failed to start backend: \(underlyingError)"

### 10. Thread-Safety

**Dispatch Queues:**
- Nutze `DispatchQueue` für Process-Operations
- Alle Process-Zugriffe auf dedizierter Queue: `DispatchQueue(label: "com.folderextractor.backend")`
- Callbacks auf Main-Queue dispatchen für UI-Updates

**Property Observers:**
- Nutze `@Published` für SwiftUI-Integration (später)
- Oder manuelle `willSet`/`didSet` für Status-Changes

### 11. Dokumentation

**Inline-Kommentare:**
- Dokumentiere jede Methode mit `///` Doc-Comments
- Erkläre Parameter und Return-Values
- Gebe Beispiele für Usage

**Header-Kommentar:**
```swift
//
//  BackendManager.swift
//  Folder Extractor
//
//  Manages the Python API server lifecycle.
//  Handles process spawning, monitoring, and graceful shutdown.
//
```

### 12. Testing-Hooks

**Debug-Properties:**
- `var debugMode: Bool = false` - Aktiviert verbose Logging
- `var pythonPath: String?` - Override für Tests
- `var scriptPath: String?` - Override für Tests

**Methode `resetForTesting()`:**
- Stoppt Process
- Resettet alle Properties
- Nur in Debug-Builds verfügbar: `#if DEBUG`

## Technische Details

### Process-Konfiguration Beispiel

```swift
let process = Process()
process.executableURL = pythonURL
process.arguments = [scriptPath, "--host", "127.0.0.1", "--port", "23456"]
process.currentDirectoryURL = projectRoot
process.environment = [
    "PYTHONUNBUFFERED": "1",
    "API_HOST": "127.0.0.1",
    "API_PORT": "23456"
]
```

### Pipe-Reading Pattern

```swift
outputPipe.fileHandleForReading.readabilityHandler = { handle in
    let data = handle.availableData
    if data.count > 0 {
        if let line = String(data: data, encoding: .utf8) {
            self.handleLogLine(line, level: .info)
        }
    }
}
```

### Pfad-Suche Strategie

1. **Bundle Resources** (Production): `Bundle.main.resourceURL/venv/bin/python3`
2. **Development Relative**: `Bundle.main.bundleURL/../../../venv/bin/python3`
3. **System Fallback**: `/usr/bin/python3`

## Abhängigkeiten

- **Foundation Framework**: Für `Process`, `Pipe`, `FileManager`, `URL`
- **Dispatch Framework**: Für `DispatchQueue` und Threading
- **Combine Framework** (optional): Für `@Published` Properties

## Sicherheitsüberlegungen

- **Sandbox Permissions**: App benötigt `com.apple.security.files.user-selected.read-write` für Dateizugriff
- **Network Permissions**: `com.apple.security.network.client` für localhost-Verbindungen
- **Process Spawning**: Keine zusätzlichen Entitlements nötig für localhost-Prozesse

## Integration mit anderen Komponenten

Der `BackendManager` wird später von:
- `AppState` genutzt für Status-Management
- `APIClient` genutzt für Health-Checks
- `FolderExtractorApp` beim App-Start initialisiert