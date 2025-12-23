# Folder Extractor - Architecture Documentation

## Overview

Folder Extractor is a German-language command-line tool for safely extracting files from subdirectories. The application has been refactored from a monolithic architecture (1201 lines in a single file) to a clean, modular architecture following best practices and design patterns.

## Architecture Principles

- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Dependency Injection**: Components receive their dependencies rather than creating them
- **Interface Segregation**: Clear interfaces define contracts between modules
- **Open/Closed Principle**: Extensible through interfaces without modifying existing code
- **DRY (Don't Repeat Yourself)**: Common functionality is extracted and reused
- **Thread Safety**: State management is thread-safe for concurrent operations

## Directory Structure

```
folder_extractor/
├── __init__.py
├── main.py               # Compatibility wrapper for legacy function names
│
├── cli/                  # Command Line Interface layer
│   ├── __init__.py
│   ├── parser.py         # Argument parsing with custom help
│   ├── interface.py      # Console interaction & progress display
│   └── app.py            # Enhanced CLI application with state management
│
├── core/                 # Business logic layer
│   ├── __init__.py
│   ├── file_discovery.py # File finding, filtering, and weblink parsing
│   ├── file_operations.py # File operations, hashing, and history management
│   ├── extractor.py      # Enhanced extraction orchestration
│   ├── state.py          # Application state interfaces
│   ├── state_manager.py  # Thread-safe state management
│   ├── progress.py       # Progress tracking with callbacks
│   └── migration.py      # Settings migration utilities
│
├── config/              # Configuration layer
│   ├── __init__.py
│   ├── constants.py     # Application constants, messages, file type mappings
│   └── settings.py      # Runtime settings management (singleton)
│
└── utils/               # Utility functions
    ├── __init__.py
    ├── path_validators.py  # Path security validation
    ├── file_validators.py  # File type and temp file validation
    └── parsers.py          # Input parsing (file types, domains, depth)
```

## Key Components

### 1. CLI Layer (`cli/`)

**Purpose**: Handle user interaction, command parsing, and presentation

- **`parser.py`**: Defines command-line arguments using argparse with custom help text
- **`interface.py`**:
  - `ConsoleInterface`: Manages user output, progress display, and confirmation dialogs
  - `create_console_interface()`: Factory function for interface creation
- **`app.py`**:
  - `EnhancedFolderExtractorCLI`: Main CLI application with state management integration
  - Handles extraction and undo workflows

### 2. Core Business Logic (`core/`)

**Purpose**: Implement the actual file extraction logic

- **`file_discovery.py`**:
  - `IFileDiscovery`: Interface for file discovery
  - `FileDiscovery`: Finds files based on criteria (depth, type, hidden)

#### File Discovery Implementation Details

**Iterative Approach with `os.walk()`:**
- Uses `os.walk(topdown=True)` for efficient directory traversal (line 82)
- **No recursion** - resistant to `RecursionError` even at depths > 1000 levels
- Single-pass traversal minimizes filesystem I/O operations

**Depth Control via `dirs[:] = []` Pattern:**
- `max_depth` parameter controls traversal depth (line 94-95)
- In-place modification of `dirs[:]` prevents `os.walk()` from descending further
- Efficient: Stops traversal early rather than filtering results post-traversal
- Example: `if current_depth >= max_depth: dirs[:] = []`

**Hidden File Filtering Optimization:**
- `include_hidden=False` prunes hidden directories at traversal time (line 98-99)
- Uses `dirs[:] = [d for d in dirs if not d.startswith('.')]`
- Performance benefit: Avoids entering hidden directory trees entirely
- Contrast to post-filtering: Saves filesystem operations

**Abort Signal Integration:**
- Checks `abort_signal.is_set()` in each iteration (line 84)
- Enables graceful cancellation of long-running operations
- Thread-safe via `threading.Event`

**Performance Characteristics:**
- Time Complexity: O(n) where n = total files in traversed tree
- Space Complexity: O(d) where d = maximum depth (call stack is constant)
- Benchmarks: Handles 1500+ levels without performance degradation
- Comparison: ~2-3x faster than recursive implementation for deep structures
  
- **`file_operations.py`**:
  - `IFileOperations`: Interface for file operations
  - `FileOperations`: File operations including:
    - `move_file()`: Atomic file moving (rename or copy+delete fallback)
    - `generate_unique_name()`: Creates unique filenames for duplicates
    - `calculate_file_hash()`: SHA256 hash calculation for deduplication
    - `build_hash_index()`: Builds hash index for global deduplication
    - `determine_type_folder()`: Maps file extensions to folder names
  - `FileMover`: High-level file moving with:
    - Progress tracking and abort signal support
    - Content-based deduplication (`--deduplicate`)
    - Global deduplication across entire target (`--global-dedup`)
    - Sort-by-type functionality
  - `HistoryManager`: Manages operation history for undo
    - Central storage in `~/.config/folder_extractor/history/`
    - Immutable file protection on macOS
    - Legacy file migration

- **`extractor.py`**:
  - `IEnhancedExtractor`: Interface for enhanced extraction operations
  - `EnhancedFileExtractor`: Coordinates file discovery and moving with state tracking
  - `EnhancedExtractionOrchestrator`: High-level extraction workflow with:
    - Security validation
    - User confirmation
    - Progress callbacks
    - Empty directory cleanup

- **`state_manager.py`**:
  - `IStateManager`: Interface for state management
  - `StateManager`: Thread-safe state management with operation tracking
  - `OperationStats`: Statistics for operations
  - `ManagedOperation`: Context manager for operation lifecycle

- **`progress.py`**:
  - `IProgressTracker`: Interface for progress tracking
  - `ProgressTracker`: Track and report operation progress
  - `CompositeProgressTracker`: Aggregate multiple progress trackers

### 3. Configuration (`config/`)

**Purpose**: Centralize configuration and constants

- **`constants.py`**: All string constants, messages, and file type mappings
- **`settings.py`**: Runtime settings management (singleton pattern)

### 4. Utilities (`utils/`)

**Purpose**: Shared utility functions

- **`path_validators.py`**: Security validation for paths (Desktop/Downloads/Documents only)
- **`file_validators.py`**: File type validation, temp file detection, system file filtering
- **`parsers.py`**: Input parsing utilities:
  - `parse_file_types()`: Parses comma-separated file extensions
  - `parse_domains()`: Parses and normalizes domain filters
  - `parse_depth()`: Validates and parses depth parameter

## Design Patterns Used

### 1. **Interface Segregation**
Each module defines clear interfaces (abstract base classes) that specify contracts:
```python
class IFileDiscovery(ABC):
    @abstractmethod
    def find_files(self, directory: str, ...) -> List[str]:
        pass
```

### 2. **Dependency Injection**
Components receive dependencies through constructors:
```python
class FileExtractor:
    def __init__(self, file_discovery: IFileDiscovery, 
                 file_operations: IFileOperations):
        self.file_discovery = file_discovery
        self.file_operations = file_operations
```

### 3. **Factory Pattern**
Creation functions provide configured instances:
```python
def create_console_interface() -> IConsoleInterface:
    return ConsoleInterface()
```

### 4. **Singleton Pattern**
Settings and state manager use singleton pattern for global access:
```python
_state_manager_instance: Optional[StateManager] = None

def get_state_manager() -> StateManager:
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
```

### 5. **Context Manager Pattern**
Operation lifecycle management:
```python
with ManagedOperation(state_manager, "extraction") as op:
    # Perform operation
    # Automatic cleanup on exit
```

### 6. **Observer Pattern**
State manager supports event listeners:
```python
state_manager.add_listener("state_changed", callback_function)
```

### 7. **Adapter Pattern**
Migration adapters provide compatibility:
```python
class ExtractorAdapter(IExtractor):
    def __init__(self, enhanced_extractor: IEnhancedExtractor):
        self.enhanced_extractor = enhanced_extractor
```

## Deduplication Architecture

The application supports two levels of duplicate detection:

### Content-Based Deduplication (`--deduplicate`)

Detects files with identical content when they have the same name:

```
Source: folder1/photo.jpg (hash: abc123)
Target: photo.jpg (hash: abc123)
Result: Source is deleted (not moved), counted as content duplicate
```

**Algorithm:**
1. Check if destination file with same name exists
2. Calculate SHA256 hash of both files
3. If hashes match → delete source, skip move
4. If hashes differ → rename source (`photo_1.jpg`)

### Global Deduplication (`--global-dedup`)

Detects files with identical content anywhere in the target directory:

```
Source: folder1/vacation.jpg (hash: xyz789)
Target: exists as photos/beach.jpg (hash: xyz789)
Result: Source is deleted, counted as global duplicate
```

**Algorithm:**
1. Build hash index of ALL files in target directory (Phase 1)
2. For each source file:
   - Calculate hash
   - Check if hash exists in index
   - If match found → delete source, skip move
3. Update index after each successful move

**Performance Optimization:**
- Size-based pre-filtering: Only hash files with matching sizes
- Chunked reading: 8KB chunks for memory efficiency with large files
- Abort signal integration: Can cancel long indexing operations

## Data Flow

1. **User Input** → CLI Parser → Settings Configuration
2. **Execution Request** → CLI App → Orchestrator
3. **File Discovery** → FileDiscovery finds files based on criteria
4. **Validation** → Security and file validators check each file
5. **Hash Indexing** (if global-dedup) → Build index of existing files
6. **File Operations** → FileMover moves files with deduplication checks
7. **State Updates** → StateManager tracks operation progress
8. **Progress Display** → ConsoleInterface shows real-time progress
9. **History Saving** → HistoryManager saves operations for undo
10. **Cleanup** → Remove empty directories
11. **Result Display** → ConsoleInterface shows summary with duplicate counts

## Thread Safety

The application ensures thread safety through:

1. **Thread-safe State Manager**: Uses locks for concurrent access
2. **Abort Signal**: Threading.Event for safe operation cancellation
3. **Atomic Operations**: File operations are atomic where possible
4. **Progress Callbacks**: Thread-safe progress reporting

## Migration Strategy

The architecture maintains backward compatibility:

1. **Legacy Function Names**: `main.py` provides wrapper functions with original German names
2. **History Migration**: Automatic migration from local `.folder_extractor_history.json` to central config
3. **Settings Migration**: `MigrationHelper` migrates settings to state manager
4. **Interface Adapters**: Bridge between legacy and enhanced interfaces

## Testing Strategy

The modular architecture enables comprehensive testing:

1. **Unit Tests**: Test each component in isolation
2. **Integration Tests**: Test component interactions
3. **Backward Compatibility Tests**: Ensure legacy behavior preserved
4. **Performance Tests**: Benchmark critical operations

## Extension Points

The architecture is designed for extensibility:

1. **New File Discovery Strategies**: Implement `IFileDiscovery`
2. **Custom File Operations**: Implement `IFileOperations`
3. **Alternative UI**: Implement `IConsoleInterface`
4. **State Persistence**: Extend `IStateManager`
5. **Progress Visualization**: Extend `IProgressTracker`

## Performance Considerations

1. **Lazy Loading**: Components loaded only when needed
2. **Efficient File Walking**: Single pass through directory tree
3. **Batch Operations**: Progress updates batched for efficiency
4. **Memory Efficiency**: Stream processing for large file sets
5. **Iterative File Discovery**: `os.walk()` instead of recursion prevents stack overflow
6. **Early Pruning**: `dirs[:] = []` pattern stops traversal at depth/hidden boundaries
7. **Depth Calculation Optimization**: Uses `len(path.parts)` instead of `resolve()` (line 91)

## Security Considerations

1. **Path Validation**: Only operates in safe user directories
2. **No Code Execution**: No dynamic code execution
3. **Input Sanitization**: All user input validated
4. **Atomic Operations**: Prevent partial state corruption

## Future Enhancements

The modular architecture enables future enhancements:

1. **Persistent Configuration**: Save user preferences to config file (planned for v1.4.0)
2. **Improved Undo for Duplicates**: Restore deduplicated files by copying (planned for v1.4.0)
3. **GUI Frontend**: Add graphical interface using the same core
4. **Watch Mode**: Monitor directories and auto-organize new files
5. **Archive Extraction**: Transparent handling of ZIP/RAR/7z files
6. **EXIF-based Sorting**: Organize photos by capture date
7. **Plugin System**: Dynamic loading of extensions