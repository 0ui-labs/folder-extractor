# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Installation**:
```bash
# Standard installation
pip install .

# Development installation (editable)
pip install -e .

# With test dependencies
pip install -e ".[test]"
```

**Uninstall**: `pip uninstall folder-extractor`

**Run Tests**:
```bash
# All tests
python run_tests.py

# With coverage
python run_tests.py coverage

# Specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

**Linting & Formatting**:
```bash
ruff check .
ruff format .
```

## Architecture Overview

This is a German-language command-line tool for safely extracting files from subdirectories. Built with Python 3.7+ using only standard library modules (no external runtime dependencies).

### Directory Structure

```
folder_extractor/
├── main.py              # Compatibility wrapper for legacy function names
├── cli/
│   ├── app.py           # EnhancedFolderExtractorCLI - main application
│   ├── parser.py        # Argument parsing with custom help
│   └── interface.py     # Console output, progress display, confirmation
├── core/
│   ├── extractor.py     # EnhancedFileExtractor, ExtractionOrchestrator
│   ├── file_discovery.py # FileDiscovery - finds files with filters
│   ├── file_operations.py # FileOperations, FileMover, HistoryManager
│   ├── state_manager.py  # Thread-safe state management
│   ├── progress.py       # Progress tracking with callbacks
│   └── migration.py      # Settings migration utilities
├── config/
│   ├── constants.py      # Messages, file type mappings, version
│   └── settings.py       # Runtime settings (singleton)
└── utils/
    ├── path_validators.py # Security: Desktop/Downloads/Documents only
    ├── file_validators.py # Temp file detection, system file filtering
    └── parsers.py         # Input parsing (file types, domains, depth)
```

### Key Features

- **Security**: Operations restricted to Desktop/Downloads/Documents folders
- **File Discovery**: Iterative traversal with depth limits and filters
- **Deduplication**: SHA256 hash-based duplicate detection
  - `--deduplicate`: Same name + same content → skip
  - `--global-dedup`: Check against entire target directory
- **Sort by Type**: Organize files into PDF/, JPEG/, etc. folders
- **Domain Filter**: Filter .url/.webloc files by domain
- **Undo**: Full operation history with restore capability
- **Progress**: Real-time progress with Ctrl+C abort support

### Entry Point

Configured in `setup.py` as `folder-extractor=folder_extractor.main:main`

The `main.py` module provides legacy wrapper functions with German names for backward compatibility, but delegates to the modular implementation.

### Core Components

**CLI Layer** (`cli/`):
- `EnhancedFolderExtractorCLI`: Main application class
- `ConsoleInterface`: User interaction and progress display
- `ArgumentParser`: Custom parser with German help text

**Core Layer** (`core/`):
- `EnhancedFileExtractor`: Coordinates discovery and moving
- `FileDiscovery`: Uses `os.walk()` for efficient traversal
- `FileOperations`: Atomic moves, hash calculation, unique naming
- `FileMover`: High-level moving with deduplication
- `HistoryManager`: Central history storage in `~/.config/folder_extractor/`
- `StateManager`: Thread-safe operation tracking

### Data Flow

1. CLI parses arguments → Settings configured
2. Security validation (path must be in safe directories)
3. File discovery with depth, type, and domain filters
4. Hash indexing (if `--global-dedup`)
5. User confirmation
6. File moving with deduplication checks and progress
7. History saved for undo
8. Empty directories cleaned up
9. Summary displayed

### Important Implementation Details

- **Atomic Operations**: `rename()` preferred, `copy()+delete()` fallback for cross-device
- **Hash Calculation**: SHA256 with 8KB chunks for memory efficiency
- **Dedup Optimization**: Size-based pre-filtering before expensive hash calculation
- **Thread Safety**: `threading.Event()` for abort signals, locks in StateManager
- **History Protection**: Immutable flag on macOS, central storage location
- **Iterative Traversal**: `os.walk()` instead of recursion (handles 1500+ levels)

### Testing

- **Unit Tests**: `tests/unit/` - Individual component tests
- **Integration Tests**: `tests/integration/` - End-to-end workflows
- **Performance Tests**: `tests/performance/` - Benchmarks for large structures
- **Property Tests**: Hypothesis-based testing in `test_properties.py`

Coverage target: 95%+
