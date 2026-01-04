# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Installation**:
```bash
# Standard installation (CLI only with rich)
pip install .

# Development installation (editable)
pip install -e .

# With test dependencies
pip install -e ".[test]"

# API server dependencies (optional, requires Python 3.9+)
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv google-generativeai
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
pytest tests/unit/api/          # API tests
```

**Linting & Formatting**:
```bash
ruff check .
ruff format .
```

**Type Checking**:
```bash
pyright
```

> **Wichtig für Claude Code**: Nach Code-Änderungen immer `pyright` ausführen und Typfehler beheben, bevor du weitermachst. Produktivcode (`folder_extractor/`) hat strikte Regeln (Errors), Tests haben gelockerte Regeln (Warnings).

> **LSP nutzen**: Für semantische Code-Navigation (Referenzen, Definitionen, Typ-Info) das LSP-Tool bevorzugen statt Grep – es versteht den Code, nicht nur den Text.

## Architecture Overview

This is a German-language tool for safely extracting and organizing files from subdirectories. Built with Python 3.8+ with two modes:
- **CLI Mode**: Command-line interface with `rich` for enhanced terminal output
- **API Mode**: FastAPI-based REST API with WebSocket support (requires Python 3.9+ and additional dependencies)

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
│   ├── migration.py      # Settings migration utilities
│   ├── archives.py       # Archive extraction (ZIP/TAR) with Zip Slip protection
│   ├── monitor.py        # File stability monitoring for watch mode
│   ├── watch.py          # File system event handlers (watchdog-based)
│   ├── zone_manager.py   # Dropzone configuration and management
│   ├── smart_sorter.py   # AI-powered document categorization (Python 3.9+)
│   ├── ai_async.py       # Async AI client interface (Python 3.9+)
│   ├── ai_resilience.py  # AI retry/resilience logic (Python 3.9+)
│   ├── ai_prompts.py     # AI prompt generation (Python 3.9+)
│   ├── preprocessor.py   # Document preprocessing (Python 3.9+)
│   ├── security.py       # Security utilities (Python 3.9+)
│   └── memory/
│       └── graph.py      # Knowledge graph for document metadata (Python 3.9+)
├── api/                  # REST API (Python 3.9+, optional)
│   ├── server.py         # FastAPI application factory
│   ├── endpoints.py      # API endpoints (/process, /zones)
│   ├── websocket.py      # WebSocket endpoint for real-time updates
│   ├── models.py         # Pydantic request/response models
│   └── dependencies.py   # FastAPI dependency injection
├── config/
│   ├── constants.py      # Messages, file type mappings, version
│   └── settings.py       # Runtime settings (singleton)
└── utils/
    ├── path_validators.py # Security: Desktop/Downloads/Documents only
    ├── file_validators.py # Temp file detection, system file filtering
    └── parsers.py         # Input parsing (file types, domains, depth)
```

### Key Features

**Core Features** (CLI Mode):
- **Security**: Operations restricted to Desktop/Downloads/Documents folders
- **File Discovery**: Iterative traversal with depth limits and filters
- **Deduplication**: SHA256 hash-based duplicate detection
  - `--deduplicate`: Same name + same content → skip
  - `--global-dedup`: Check against entire target directory
- **Sort by Type**: Organize files into PDF/, JPEG/, etc. folders
- **Domain Filter**: Filter .url/.webloc files by domain
- **Undo**: Full operation history with restore capability
- **Progress**: Real-time progress with Ctrl+C abort support
- **Archive Extraction**: Safe ZIP/TAR extraction with path traversal protection

**Advanced Features** (requires Python 3.9+ and additional dependencies):
- **AI-Powered Smart Sorting**: Gemini-based document categorization with entity extraction
- **Watch Mode**: Automatic processing when files are added to monitored directories
- **Knowledge Graph**: Document metadata storage and entity relationship tracking
- **Dropzone Management**: Configure multiple zones with category templates
- **REST API**: FastAPI server with WebSocket for macOS app integration

### Entry Points

Configured in `setup.py`:
- `folder-extractor=folder_extractor.main:main` - CLI tool
- `folder-extractor-api=run_api:main` - API server (Python 3.9+)

The `main.py` module provides legacy wrapper functions with German names for backward compatibility, but delegates to the modular implementation.

### Core Components

**CLI Layer** (`cli/`):
- `EnhancedFolderExtractorCLI`: Main application class with archive extraction support
- `ConsoleInterface`: User interaction and progress display (uses `rich`)
- `ArgumentParser`: Custom parser with German help text

**Core Layer** (`core/`):
- `EnhancedFileExtractor`: Coordinates discovery and moving
- `FileDiscovery`: Uses `os.walk()` for efficient traversal
- `FileOperations`: Atomic moves, hash calculation, unique naming
- `FileMover`: High-level moving with deduplication
- `HistoryManager`: Central history storage in `~/.config/folder_extractor/`
- `StateManager`: Thread-safe operation tracking
- `ArchiveHandler`: Safe archive extraction (ZIP/TAR) with security validation
- `SmartSorter`: AI-powered categorization orchestrator (Python 3.9+)
- `FolderEventHandler`: File system watcher with debouncing (Python 3.9+)
- `ZoneManager`: Dropzone configuration management (Python 3.9+)

**API Layer** (`api/`, Python 3.9+):
- `create_app()`: FastAPI application factory
- REST endpoints: `/health`, `/api/v1/process`, `/api/v1/zones`, `/api/v1/watcher/*`
- WebSocket: `/ws/chat` for bidirectional real-time communication

### Data Flow

**CLI Mode**:
1. CLI parses arguments → Settings configured
2. Security validation (path must be in safe directories)
3. File discovery with depth, type, and domain filters
4. Archive extraction (if `--extract-archives`)
5. Hash indexing (if `--global-dedup`)
6. User confirmation
7. File moving with deduplication checks and progress
8. History saved for undo
9. Empty directories cleaned up
10. Summary displayed

**API/Watch Mode** (Python 3.9+):
1. File system event detected
2. Stability check (file finished writing)
3. Smart categorization (AI analysis)
4. Template-based path generation
5. File moved to target location
6. Knowledge graph updated with metadata
7. WebSocket notification sent

### Important Implementation Details

- **Atomic Operations**: `rename()` preferred, `copy()+delete()` fallback for cross-device
- **Hash Calculation**: SHA256 with 8KB chunks for memory efficiency
- **Dedup Optimization**: Size-based pre-filtering before expensive hash calculation
- **Thread Safety**: `threading.Event()` for abort signals, locks in StateManager
- **History Protection**: Immutable flag on macOS, central storage location
- **Iterative Traversal**: `os.walk()` instead of recursion (handles 1500+ levels)
- **Zip Slip Protection**: All archive paths validated against target directory
- **AI Rate Limiting**: Exponential backoff with resilience patterns (Python 3.9+)
- **Watch Debouncing**: File stability monitoring to avoid incomplete writes (Python 3.9+)

### Testing

- **Unit Tests**: `tests/unit/` - Individual component tests
  - `tests/unit/api/` - API-specific tests (FastAPI endpoints, WebSocket)
- **Integration Tests**: `tests/integration/` - End-to-end workflows
  - Archive extraction, smart sorting, watch mode
- **Performance Tests**: `tests/performance/` - Benchmarks for large structures
- **Property Tests**: Hypothesis-based testing in `test_properties.py`
- **Security Tests**: Zip Slip, path traversal, validation edge cases

Coverage target: 90%+ (some AI/API modules excluded on Python 3.8, see `pyproject.toml`)

### Python Version Compatibility

- **Python 3.8**: CLI mode with all core features (extraction, deduplication, sorting)
- **Python 3.9+**: Full feature set including AI sorting, watch mode, and REST API
  - AI modules require `google-generativeai` which only supports Python 3.9+
  - These modules are excluded from coverage on Python 3.8 (see `pyproject.toml`)

### Dependencies

**Runtime (CLI Mode)**:
- `rich>=13.0.0` - Enhanced terminal output (progress bars, tables, formatting)

**Optional (API/AI Mode, Python 3.9+)**:
- `fastapi` - REST API framework
- `uvicorn[standard]` - ASGI server
- `pydantic>=2.0.0` - Data validation
- `websockets` - WebSocket support
- `python-dotenv` - Environment configuration
- `google-generativeai` - Gemini AI client
- `watchdog` - File system monitoring

**Development**:
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `pytest-benchmark>=4.0` - Performance benchmarking
- `pytest-xdist>=3.0` - Parallel test execution
- `hypothesis>=6.0` - Property-based testing
