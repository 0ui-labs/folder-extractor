# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Installation**: 
```bash
# Standard installation
pip install .

# Development installation (editable)
pip install -e .
```

**Uninstall**: `pip uninstall folder-extractor`

**Direct usage without installation**: `python folder_extractor/main.py [options]`

## Architecture Overview

This is a German-language command-line tool for safely extracting files from subdirectories. Built with pure Python (3.7+) using only standard library modules - no external dependencies.

### Key Components

**Main Module** (`folder_extractor/main.py`): Single-file implementation containing all functionality:
- Security checks restricting operation to Desktop/Downloads/Documents folders
- Recursive file discovery with configurable depth limits
- File type filtering (e.g., extract only PDFs, images, etc.)
- Domain filtering for web links (.url, .webloc files)
- Duplicate handling with automatic renaming (_1, _2, etc.)
- Sort-by-type mode organizing files into type-specific folders
- Undo functionality tracking all operations in JSON history
- ESC key interruption support with proper terminal handling
- Empty folder cleanup after extraction

**Entry Point**: Configured in `setup.py` as `folder-extractor=folder_extractor.main:main`

### Core Functions

- `ist_sicherer_pfad()`: Validates execution is in safe user directories only
- `finde_dateien()`: Recursive file discovery with depth control and filtering
- `verschiebe_dateien()` / `verschiebe_dateien_sortiert()`: File moving with atomic operations
- `keyboard_listener()`: ESC key monitoring in separate thread
- `speichere_verlauf()` / `undo_operationen()`: Operation history for undo capability
- `pruefe_weblink_domain()`: Domain filtering for .url/.webloc files

### Data Flow

1. Security validation of current directory
2. File discovery based on depth, type, and domain filters  
3. User confirmation with preview showing planned operations
4. File movement with progress display and ESC interruption support
5. History saved to `.folder_extractor_history.json` for undo
6. Empty folder cleanup (unless type filter is active)

### Important Implementation Details

- Uses atomic file operations (rename when possible, copy+delete fallback for cross-device)
- Terminal settings saved/restored for proper ESC key handling  
- Ignores system files (.DS_Store, .git, temporary downloads, etc.)
- Thread-safe abort mechanism using `threading.Event()`
- Comprehensive help text with German examples and explanations