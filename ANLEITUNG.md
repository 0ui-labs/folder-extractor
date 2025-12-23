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
| **Ctrl+C** | Operation abbrechen (während des Verschiebens) |
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

---

## Zusammenfassung

1. **Navigiere** zum gewünschten Ordner: `cd ~/Downloads/MeinOrdner`
2. **Teste** zuerst: `folder-extractor --dry-run`
3. **Führe aus**: `folder-extractor [OPTIONEN]`
4. **Rückgängig** bei Bedarf: `folder-extractor --undo`

Bei Fragen: `folder-extractor --help`

---

*Viel Erfolg beim Aufräumen!* 🗂️
