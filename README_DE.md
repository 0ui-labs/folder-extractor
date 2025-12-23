
# 🗂️ Folder Extractor

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-D7FF64.svg)](https://github.com/astral-sh/ruff)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-none-success)](requirements.txt)

> **Aufräumen ohne Angst.** Das sichere Tool zum Extrahieren, Sortieren und Organisieren von Dateien aus tief verschachtelten Ordnerstrukturen.

Folder Extractor holt Dateien aus Unterordnern in das aktuelle Verzeichnis ("Flattening"), sortiert sie auf Wunsch und räumt leere Ordner auf. Es wurde mit einem primären Ziel entwickelt: **Sicherheit.**

---

## ✨ Warum Folder Extractor?

Die meisten Skripte dieser Art sind "Quick & Dirty" und gefährlich. Folder Extractor ist anders:

*   🛡️ **Safety First:** Läuft **nur** in sicheren Ordnern (Desktop, Downloads, Documents). Verhindert versehentliches Zerstören von Systemdateien.
*   ↩️ **Time Machine:** Enthält eine **Undo-Funktion**. Fehler gemacht? Ein Befehl macht alles rückgängig.
*   🧠 **Intelligent:** Erkennt Duplikate und benennt sie automatisch um, statt sie zu überschreiben.
*   🔄 **Smart Dedup:** Erkennt identische Dateien anhand des Inhalts (SHA256-Hash) – keine doppelten Kopien mehr.
*   ⚡ **Zero Config:** Keine Abhängigkeiten. Keine Konfigurationsdateien. Installieren und starten.

## 🚀 Schnellstart

### Installation

Das Tool nutzt nur die Python Standard Library (keine externen Abhängigkeiten!).

```bash
# Repository klonen & installieren
git clone https://github.com/your-username/folder-extractor.git
cd folder-extractor
pip install .
```

### Verwendung

```bash
# Einfach ausführen (interaktiv)
folder-extractor

# Oder spezifische Aufgaben automatisieren
folder-extractor --sort-by-type --depth 2
```

---

## 💡 Anwendungsbeispiele

### 1. Chaos beseitigen ("Flattening")
Sie haben einen Ordner mit 50 Unterordnern, wollen aber alle Dateien in einem Ordner haben?
```bash
folder-extractor
```
*Verschiebt alle Dateien aus Unterordnern nach oben und löscht die leeren Hüllen.*

### 2. Downloads organisieren
Ihren Download-Ordner aufräumen und Dateien direkt in Kategorien (PDF, JPG, DOCX...) sortieren?
```bash
folder-extractor --sort-by-type
```
*Erstellt Ordner wie `PDF/`, `IMAGES/`, `ARCHIVE/` und sortiert die Dateien ein.*

### 3. Gezieltes Extrahieren
Sie brauchen nur die PDFs aus einem tiefen Projektarchiv?
```bash
folder-extractor --type pdf --depth 3
```
*Holt nur `.pdf` Dateien, maximal 3 Ebenen tief. Alles andere bleibt unberührt.*

### 4. Link-Sammlung bereinigen
Sammeln Sie alle YouTube-Links aus verschiedenen `.url` oder `.webloc` Dateien?
```bash
folder-extractor --type url,webloc --domain youtube.com
```

### 5. Duplikate eliminieren
Sie haben dieselben Fotos in 10 verschiedenen Ordnern?
```bash
folder-extractor --deduplicate --global-dedup
```
*Erkennt identische Dateien anhand des Inhalts und behält nur eine Kopie.*

### 6. "Ups, das wollte ich nicht!"
Haben Sie versehentlich Dateien extrahiert, die dort bleiben sollten?
```bash
folder-extractor --undo
```
*Stellt den ursprünglichen Zustand wieder her.*

---

## 🛠️ Alle Optionen

| Option | Beschreibung |
|--------|--------------|
| `--dry-run`, `-n` | **Testlauf.** Zeigt nur an, was passieren würde (keine Änderungen). |
| `--undo`, `-u` | Macht die letzte Operation in diesem Ordner rückgängig. |
| `--sort-by-type`, `-s` | Sortiert Dateien in Unterordner basierend auf ihrem Typ. |
| `--depth`, `-d` | Maximale Suchtiefe (0 = unbegrenzt). |
| `--type`, `-t` | Filtert nach Dateiendungen (z.B. `pdf,jpg`). |
| `--domain` | Filtert Web-Links nach Domain (nur für `.url`/`.webloc`). |
| `--include-hidden` | Bezieht versteckte Dateien (starten mit `.`) mit ein. |
| `--deduplicate` | Erkennt identische Dateien (Hash-Vergleich) und vermeidet Duplikate. |
| `--global-dedup` | Globale Duplikat-Prüfung über gesamten Zielordner. |
| `--version`, `-v` | Zeigt die installierte Version an. |

---

## 🔒 Sicherheitskonzept

Um Datenverlust zu vermeiden, implementiert Folder Extractor strenge Regeln:

1.  **Whitelist-Pfade:** Operationen werden verweigert, wenn sie nicht innerhalb von `~/Desktop`, `~/Downloads` oder `~/Documents` stattfinden.
2.  **Systemschutz:** Ignoriert automatisch Systemdateien wie `.DS_Store`, `Thumbs.db` und `.git`-Verzeichnisse.
3.  **Duplikat-Schutz:** Existiert `datei.txt` bereits, wird die neue Datei `datei_1.txt` genannt. Es wird **niemals** überschrieben.
4.  **Bestätigung:** Vor jeder destruktiven Aktion (außer im Undo-Modus) muss der Benutzer explizit zustimmen.

---

## 💻 Entwicklung

Wir freuen uns über Pull Requests! Das Projekt ist modular aufgebaut und umfassend getestet.

```bash
# Entwicklungsumgebung aufsetzen
pip install -e ".[test]"

# Tests ausführen
pytest tests/
```

Detaillierte Infos zur Architektur finden Sie in [ARCHITECTURE.md](ARCHITECTURE.md).

## 📄 Lizenz

MIT License - Copyright (c) 2024 Philipp Briese

---
*Made with ❤️ and Python.*

***

