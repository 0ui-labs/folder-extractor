# Folder Extractor Test Suite

## Übersicht

Umfassende Test Suite für Folder Extractor mit Unit-, Integration- und Performance-Tests.

## Test-Struktur

```
tests/
├── unit/                           # Unit Tests für einzelne Module
│   ├── test_cli_app.py             # CLI Application Tests
│   ├── test_cli_interface.py       # CLI Interface Tests
│   ├── test_cli_parser.py          # Argument Parser Tests
│   ├── test_core_extractor.py      # Core Extractor Tests
│   ├── test_core_extractor_enhanced.py  # Enhanced Extractor Tests
│   ├── test_core_file_discovery.py # File Discovery Tests
│   ├── test_core_file_operations.py # File Operations Tests
│   ├── test_core_state.py          # State Management Tests
│   ├── test_deep_structures.py     # Deep Directory Tests
│   ├── test_file_operations.py     # Legacy File Operations
│   ├── test_global_dedup.py        # Global Deduplication Tests
│   ├── test_hashing.py             # File Hashing Tests (SHA256)
│   ├── test_new_parsers.py         # Parser Tests
│   ├── test_progress.py            # Progress Tracking Tests
│   ├── test_properties.py          # Property-based Tests
│   ├── test_settings.py            # Settings Tests
│   ├── test_state_manager.py       # State Manager Tests
│   ├── test_validators.py          # Validator Tests
│   └── test_conftest_fixtures.py   # Fixture Tests
├── integration/                    # Integration Tests für Workflows
│   ├── test_backward_compatibility.py  # Rückwärtskompatibilität
│   └── test_extraction_workflow.py     # End-to-End Workflows
└── performance/                    # Performance Benchmarks
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
- **CLI Tests**: Parser, Interface und Application Tests
- **Core Tests**: Extractor, File Discovery, File Operations
- **State Management**: State Manager und Progress Tracking
- **Hashing & Dedup**: SHA256-Hashing und Duplikat-Erkennung
- **Validators & Parsers**: Eingabe-Validierung und Parsing
- **Settings & Migration**: Konfiguration und Legacy-Migration

### Integration Tests
- **Extraction Workflow**: End-to-End Tests des kompletten Workflows
- **Backward Compatibility**: Tests für Rückwärtskompatibilität

### Performance Benchmarks
- Dateisuche in verschiedenen Strukturen
- Hash-Berechnung für große Dateien
- Verschieben vieler Dateien
- Eindeutige Namengenerierung

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