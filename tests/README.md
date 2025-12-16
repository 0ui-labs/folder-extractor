# Folder Extractor Test Suite

## Übersicht

Diese Test Suite dokumentiert und verifiziert das aktuelle Verhalten von Folder Extractor vor der geplanten Refaktorierung.

## Test-Struktur

```
tests/
├── unit/                    # Unit Tests für einzelne Funktionen
│   ├── test_parsing_functions.py
│   └── test_file_operations.py
├── integration/             # Integration Tests für Workflows
│   ├── test_main_functionality.py
│   ├── test_file_moving.py
│   ├── test_undo_functionality.py
│   ├── test_abort_handling.py
│   ├── test_terminal_handling.py
│   └── test_edge_cases.py
└── performance/            # Performance Benchmarks
    └── test_benchmarks.py
```

## Tests ausführen

### Alle Tests
```bash
python run_tests.py
```

### Nur Unit Tests
```bash
python run_tests.py unit
```

### Nur Integration Tests
```bash
python run_tests.py integration
```

### Performance Benchmarks
```bash
python run_tests.py performance
```

### Mit Coverage Report
```bash
python run_tests.py coverage
```

## Test-Kategorien

### Unit Tests
- **Parsing Functions**: Test der Eingabe-Parser für Dateitypen und Domains
- **File Operations**: Test von Dateioperationen wie eindeutige Namengenerierung

### Integration Tests
- **Main Functionality**: Test der Hauptfunktionen (Dateisuche, Sicherheitsvalidierung)
- **File Moving**: Test des Dateiverschiebens und Sortierens
- **Undo Functionality**: Test der Undo-Operationen
- **Abort Handling**: Test der ESC-Taste Abbruchfunktion
- **Terminal Handling**: Test der Terminal-Einstellungen
- **Edge Cases**: Test von Spezialfällen (Unicode, große Dateimengen)

### Performance Benchmarks
- Dateisuche in verschiedenen Strukturen
- Verschieben vieler Dateien
- Eindeutige Namengenerierung
- Leere Ordner Bereinigung

## Wichtige Test-Fixtures

- `temp_dir`: Temporäres Verzeichnis für Tests
- `test_file_structure`: Standard-Testdateistruktur
- `safe_test_dir`: Sicheres Testverzeichnis auf Desktop
- `mock_user_input`: Mock für Benutzereingaben

## Hinweise

1. Tests laufen nur in sicheren Verzeichnissen (Desktop/Downloads/Documents)
2. Terminal-Tests werden auf Windows übersprungen
3. Performance-Tests erstellen temporäre Dateien auf dem Desktop
4. Alle Test-Dateien werden nach dem Test automatisch bereinigt