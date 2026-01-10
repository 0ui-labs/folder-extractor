# Folder Extractor - Bedienungsanleitung

**Version 1.3.3** | Von Philipp Briese

---

## Was macht dieses Tool?

Der **Folder Extractor** hilft dir dabei, Dateien aus verschachtelten Unterordnern herauszuholen und in einem Ordner zu sammeln. Stell dir vor, du hast viele Ordner mit Dateien darin – dieses Tool bringt alle Dateien auf eine Ebene.

### Vorher:
```
📁 Downloads/
   📁 Projekt1/
      📄 dokument.pdf
      📁 Bilder/
         🖼 foto.jpg
   📁 Projekt2/
      📄 notizen.txt
```

### Nachher:
```
📁 Downloads/
   📄 dokument.pdf
   🖼 foto.jpg
   📄 notizen.txt
```

---

## Sicherheitshinweis

Das Tool funktioniert **nur** in diesen Ordnern:
- **Desktop**
- **Downloads**
- **Documents**

Das schützt dich davor, versehentlich wichtige Systemdateien zu verschieben.

---

## Installation

```bash
# Im Terminal eingeben:
pip install .

# Zum Deinstallieren:
pip uninstall folder-extractor
```

---

## Grundlegende Verwendung

### 1. Alle Dateien extrahieren

Navigiere im Terminal zu deinem Ordner und führe aus:

```bash
cd ~/Downloads/MeinOrdner
folder-extractor
```

Das Tool zeigt dir:
1. Wie viele Dateien gefunden wurden
2. Fragt, ob du fortfahren möchtest (j/n)
3. Verschiebt die Dateien und zeigt den Fortschritt

---

## Optionen und Beispiele

### Testlauf (nichts wird verschoben)

Willst du erst sehen, was passieren würde?

```bash
folder-extractor --dry-run
```
oder kurz:
```bash
folder-extractor -n
```

**Tipp:** Immer zuerst einen Testlauf machen, um sicher zu gehen!

---

### Nur bestimmte Dateitypen extrahieren

Du willst nur PDFs und Bilder? Kein Problem:

```bash
folder-extractor --type pdf,jpg,png
```
oder kurz:
```bash
folder-extractor -t pdf,jpg,png
```

**Weitere Beispiele:**
```bash
# Nur PDFs
folder-extractor -t pdf

# Nur Videos
folder-extractor -t mp4,avi,mkv,mov

# Nur Musik
folder-extractor -t mp3,wav,flac

# Nur Office-Dokumente
folder-extractor -t pdf,doc,docx,xls,xlsx
```

---

### Nach Dateityp sortieren

Statt alle Dateien flach abzulegen, kannst du sie automatisch in Typ-Ordner sortieren lassen:

```bash
folder-extractor --sort-by-type
```
oder kurz:
```bash
folder-extractor -s
```

**Ergebnis:**
```
📁 Downloads/
   📁 PDF/
      📄 dokument.pdf
      📄 rechnung.pdf
   📁 JPEG/
      🖼 foto1.jpg
      🖼 foto2.jpg
   📁 VIDEO/
      🎬 video.mp4
```

---

### Ordnertiefe begrenzen

Du willst nur Dateien aus direkten Unterordnern (nicht aus Unter-Unterordnern)?

```bash
folder-extractor --depth 1
```
oder kurz:
```bash
folder-extractor -d 1
```

**Beispiel:**
- `--depth 1` = Nur direkte Unterordner
- `--depth 2` = Bis zu 2 Ebenen tief
- `--depth 0` = Unbegrenzt (Standard)

---

### Duplikate vermeiden

Hast du identische Dateien in verschiedenen Ordnern? Mit dieser Option werden Duplikate (gleicher Inhalt) nicht mehrfach kopiert:

```bash
folder-extractor --deduplicate
```

**Was passiert bei Duplikaten?**
- Normale Duplikate (gleicher Name, anderer Inhalt): Werden umbenannt (`foto_1.jpg`, `foto_2.jpg`)
- Echte Duplikate (gleicher Inhalt): Werden übersprungen

---

### Globale Deduplizierung

Diese Option prüft **alle** Dateien im Zielordner auf Duplikate – auch die, die schon da sind:

```bash
folder-extractor --global-dedup
```

⚠️ **Achtung:** Bei vielen Dateien kann das länger dauern!

---

### Archive automatisch entpacken

Hast du ZIP-, TAR- oder GZ-Dateien in deinen Unterordnern? Mit dieser Option werden sie automatisch entpackt:

```bash
folder-extractor --extract-archives
```

**Was passiert:**
1. Archive werden erkannt (ZIP, TAR, TAR.GZ, TGZ)
2. Inhalte werden sicher extrahiert (mit Schutz gegen Zip Slip Angriffe)
3. Extrahierte Dateien werden wie normale Dateien behandelt
4. Leere Archiv-Dateien bleiben standardmäßig erhalten

**Archive nach dem Entpacken löschen:**
```bash
folder-extractor --extract-archives --delete-archives
```

⚠️ **Sicherheitshinweis:** `--delete-archives` funktioniert nur zusammen mit `--extract-archives` und löscht die Original-Archive nach erfolgreichem Entpacken.

**Kombiniert mit anderen Optionen:**
```bash
# Archive entpacken und nach Typ sortieren
folder-extractor --extract-archives --sort-by-type

# Nur Archive mit bestimmten Inhalten extrahieren
folder-extractor --extract-archives --type pdf,jpg
```

---

### Ordner automatisch überwachen (Watch Mode)

Du möchtest, dass neue Dateien automatisch verarbeitet werden, sobald sie in einem Ordner landen?

```bash
folder-extractor --watch
```

**Was passiert:**
1. Das Tool überwacht den aktuellen Ordner
2. Neue Dateien werden automatisch erkannt
3. Nach kurzer Wartezeit (um sicherzustellen, dass der Download fertig ist) werden sie verarbeitet
4. Das Tool läuft weiter, bis du Ctrl+C drückst

**Kombiniert mit anderen Optionen:**
```bash
# Überwachen und nach Typ sortieren
folder-extractor --watch --sort-by-type

# Überwachen und Archive entpacken
folder-extractor --watch --extract-archives --delete-archives
```

⚠️ **Hinweis:** Watch Mode ist ideal für Download-Ordner, die du regelmäßig organisieren möchtest.

---

### Knowledge Graph abfragen

Wenn du AI-Features aktiviert hast (Python 3.9+ mit `google-generativeai`), kannst du deine Dateien mit natürlicher Sprache abfragen:

```bash
# Nach Dokumenttypen suchen
folder-extractor --ask "Welche Versicherungsdokumente habe ich?"

# Nach Sender filtern
folder-extractor --ask "Zeig mir Rechnungen von Apple"

# Nach Zeitraum suchen
folder-extractor --ask "Welche Dokumente habe ich aus 2024?"
```

**Voraussetzungen:**
- Python 3.9 oder höher
- Installation: `pip install google-generativeai kuzu`
- API-Key konfiguriert (siehe API-Dokumentation)

---

### Nur bestimmte Web-Links

Hast du `.url` oder `.webloc` Dateien (Browser-Lesezeichen) und willst nur bestimmte Domains?

```bash
# Nur YouTube-Links
folder-extractor --type url,webloc --domain youtube.com

# Nur GitHub-Links
folder-extractor --type url,webloc --domain github.com

# Mehrere Domains
folder-extractor --type url --domain youtube.com,vimeo.com
```

---

### Versteckte Dateien einbeziehen

Normalerweise werden versteckte Dateien (beginnen mit `.`) ignoriert. So schließt du sie ein:

```bash
folder-extractor --include-hidden
```

---

### Letzte Operation rückgängig machen

Etwas ist schiefgelaufen? Kein Problem:

```bash
folder-extractor --undo
```
oder kurz:
```bash
folder-extractor -u
```

Das Tool merkt sich die letzte Operation und kann sie vollständig rückgängig machen.

---

## Kombinierte Beispiele

### Aufräumen von Downloads

```bash
cd ~/Downloads
folder-extractor --sort-by-type --deduplicate
```
→ Sortiert alle Dateien nach Typ und vermeidet Duplikate.

---

### Fotos aus verschachtelten Ordnern sammeln

```bash
cd ~/Documents/Fotos
folder-extractor --type jpg,jpeg,png,heic --deduplicate
```
→ Sammelt alle Bilder und entfernt doppelte.

---

### Archive organisieren

```bash
cd ~/Downloads
folder-extractor --extract-archives --delete-archives --sort-by-type
```
→ Entpackt alle Archive, löscht die Originale und sortiert den Inhalt nach Typ.

---

### Download-Ordner automatisch organisieren

```bash
cd ~/Downloads
folder-extractor --watch --sort-by-type --extract-archives
```
→ Überwacht den Download-Ordner, sortiert neue Dateien nach Typ und entpackt Archive automatisch.

---

### Sicheres Testen

```bash
cd ~/Downloads/MeinProjekt
folder-extractor --dry-run --type pdf
```
→ Zeigt, welche PDFs verschoben würden, ohne etwas zu tun.

---

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| **Ctrl+C** | Operation abbrechen (während des Verschiebens oder im Watch Mode) |
| **j** | Ja, fortfahren |
| **n** | Nein, abbrechen |

---

## Alle Optionen auf einen Blick

| Option | Kurzform | Beschreibung |
|--------|----------|--------------|
| `--help` | `-h` | Hilfe anzeigen |
| `--version` | `-v` | Version anzeigen |
| `--depth ZAHL` | `-d ZAHL` | Maximale Ordnertiefe (0 = unbegrenzt) |
| `--type TYPEN` | `-t TYPEN` | Nur bestimmte Dateitypen |
| `--dry-run` | `-n` | Testlauf ohne Verschieben |
| `--sort-by-type` | `-s` | Nach Typ sortieren |
| `--undo` | `-u` | Letzte Operation rückgängig machen |
| `--include-hidden` | – | Versteckte Dateien einbeziehen |
| `--deduplicate` | – | Inhalts-Duplikate vermeiden |
| `--global-dedup` | – | Globale Duplikat-Prüfung |
| `--domain DOMAINS` | – | Nur Web-Links von Domains |
| `--extract-archives` | – | Archive (ZIP/TAR/GZ) entpacken |
| `--delete-archives` | – | Archive nach Entpacken löschen |
| `--watch` | – | Ordner überwachen (automatische Verarbeitung) |
| `--ask FRAGE` | – | Knowledge Graph abfragen (Python 3.9+) |

---

## Typische Arbeitsabläufe

### 1. Downloads aufräumen (sicher)

```bash
cd ~/Downloads

# Erst testen
folder-extractor --dry-run --sort-by-type

# Wenn alles gut aussieht, ausführen
folder-extractor --sort-by-type --deduplicate
```

### 2. Projektordner bereinigen

```bash
cd ~/Documents/Projekt

# Nur Dokumente sammeln
folder-extractor --type pdf,doc,docx,txt

# Falls nötig: rückgängig machen
folder-extractor --undo
```

### 3. Foto-Sammlung konsolidieren

```bash
cd ~/Pictures/Urlaub

# Alle Bilder sammeln, Duplikate entfernen
folder-extractor --type jpg,jpeg,png,heic,gif --deduplicate --global-dedup
```

### 4. Backup-Archive organisieren

```bash
cd ~/Documents/Backups

# Archive entpacken und nach Typ sortieren
folder-extractor --extract-archives --sort-by-type

# Originale behalten für Sicherheit
# ODER mit --delete-archives die Archive nach dem Entpacken löschen
```

### 5. Download-Ordner automatisch organisieren

```bash
cd ~/Downloads

# Automatische Überwachung mit Sortierung
folder-extractor --watch --sort-by-type --extract-archives
# Mit Ctrl+C beenden, wenn du fertig bist
```

---

## Fehlerbehebung

### "Sicherheitswarnung: Ordner nicht erlaubt"

**Lösung:** Wechsle zu Desktop, Downloads oder Documents:
```bash
cd ~/Downloads
```

### "Keine Dateien gefunden"

**Mögliche Ursachen:**
- Keine Unterordner vorhanden
- Falscher Dateityp-Filter
- Zu geringe Tiefe eingestellt

**Lösung:** Prüfe mit `ls -la` den Ordnerinhalt.

### "Operation abgebrochen"

Wenn du während des Verschiebens **Ctrl+C** drückst, stoppt die Operation. Bereits verschobene Dateien bleiben verschoben.

**Lösung:** Mit `folder-extractor --undo` kannst du alles rückgängig machen.

### "Archive konnte nicht entpackt werden"

**Mögliche Ursachen:**
- Beschädigtes Archiv
- Nicht unterstütztes Format
- Keine Berechtigung zum Lesen

**Lösung:**
- Prüfe die Archiv-Integrität
- Unterstützte Formate: ZIP, TAR, TAR.GZ, TGZ
- Prüfe Dateiberechtigungen mit `ls -l`

### Watch Mode reagiert nicht

**Mögliche Ursachen:**
- Datei wird noch geschrieben (Tool wartet auf Stabilität)
- Datei ist in einem versteckten Ordner (verwende `--include-hidden`)

**Lösung:** Warte kurz oder prüfe die Logs in der Konsole.

---

## Erweiterte Features (Python 3.9+)

Einige Features benötigen Python 3.9 oder höher und zusätzliche Pakete:

### AI-Powered Smart Sorting
Automatische Kategorisierung von Dokumenten mit Google Gemini AI.

**Installation:**
```bash
pip install google-generativeai kuzu
```

**Konfiguration:**
API-Key in `.env` Datei oder Umgebungsvariable setzen.

### REST API Server
Für Integration mit nativen macOS/iOS Apps.

**Installation:**
```bash
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv
```

**Starten:**
```bash
folder-extractor-api
```

Details siehe README.md Abschnitt "API Server".

---

## Zusammenfassung

1. **Navigiere** zum gewünschten Ordner: `cd ~/Downloads/MeinOrdner`
2. **Teste** zuerst: `folder-extractor --dry-run`
3. **Führe aus**: `folder-extractor [OPTIONEN]`
4. **Rückgängig** bei Bedarf: `folder-extractor --undo`

Bei Fragen: `folder-extractor --help`

---

*Viel Erfolg beim Aufräumen!* 🗂️
