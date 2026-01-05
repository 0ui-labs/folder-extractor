# Folder Extractor - Architecture Documentation

## Overview

Folder Extractor is a German-language tool for safely extracting and organizing files from subdirectories. The application has evolved from a monolithic architecture (1201 lines in a single file) to a clean, modular dual-mode architecture following best practices and design patterns.

**Two Operating Modes:**
- **CLI Mode**: Command-line interface with enhanced terminal output (Python 3.8+)
- **API Mode**: REST API with WebSocket support for native app integration (Python 3.9+)

## Architecture Principles

- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Dependency Injection**: Components receive their dependencies rather than creating them
- **Interface Segregation**: Clear interfaces define contracts between modules
- **Open/Closed Principle**: Extensible through interfaces without modifying existing code
- **DRY (Don't Repeat Yourself)**: Common functionality is extracted and reused
- **Thread Safety**: State management is thread-safe for concurrent operations
- **Security First**: Path validation, Zip Slip protection, and input sanitization throughout

## Directory Structure

```
folder_extractor/
├── __init__.py
├── main.py               # Compatibility wrapper for legacy function names
│
├── cli/                  # Command Line Interface layer
│   ├── __init__.py
│   ├── parser.py         # Argument parsing with custom help
│   ├── interface.py      # Console interaction & progress display (uses rich)
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
│       └── graph.py      # Knowledge graph for document metadata (KùzuDB)
│
├── config/              # Configuration layer
│   ├── __init__.py
│   ├── constants.py     # Application constants, messages, file type mappings
│   └── settings.py      # Runtime settings management (singleton)
│
├── utils/               # Utility functions
│   ├── __init__.py
│   ├── path_validators.py  # Path security validation
│   ├── file_validators.py  # File type and temp file validation
│   └── parsers.py          # Input parsing (file types, domains, depth)
│
└── api/                 # REST API layer (Python 3.9+, optional)
    ├── __init__.py
    ├── server.py        # FastAPI application factory
    ├── endpoints.py     # REST endpoints (/process, /zones, /watcher)
    ├── websocket.py     # WebSocket connection manager for real-time updates
    ├── models.py        # Pydantic request/response models
    └── dependencies.py  # FastAPI dependency injection functions
```

## Key Components

### 1. CLI Layer (`cli/`)

**Purpose**: Handle user interaction, command parsing, and presentation

- **`parser.py`**: Defines command-line arguments using argparse with custom help text
- **`interface.py`**:
  - `ConsoleInterface`: Manages user output, progress display, and confirmation dialogs
  - Uses `rich` library for enhanced terminal output (progress bars, tables, formatting)
  - `create_console_interface()`: Factory function for interface creation
- **`app.py`**:
  - `EnhancedFolderExtractorCLI`: Main CLI application with state management integration
  - Handles extraction, undo, and archive extraction workflows

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
    - Archive extraction support

- **`state_manager.py`**:
  - `IStateManager`: Interface for state management
  - `StateManager`: Thread-safe state management with operation tracking
  - `OperationStats`: Statistics for operations
  - `ManagedOperation`: Context manager for operation lifecycle

- **`progress.py`**:
  - `IProgressTracker`: Interface for progress tracking
  - `ProgressTracker`: Track and report operation progress
  - `CompositeProgressTracker`: Aggregate multiple progress trackers

- **`archives.py`**:
  - `IArchiveHandler`: Interface for archive handlers
  - `ZipArchiveHandler`: Safe ZIP extraction with Zip Slip protection
  - `TarArchiveHandler`: Safe TAR extraction with path traversal prevention
  - Security validation ensures all extracted paths stay within target directory

- **`monitor.py`**:
  - `StabilityMonitor`: Monitors file stability (finished writing) before processing
  - Prevents processing of incomplete downloads or in-progress file transfers
  - Configurable stability timeout and check interval

- **`watch.py`** (Python 3.9+):
  - `FolderEventHandler`: Basic file system event handler with debouncing
  - `SmartFolderEventHandler`: AI-powered event handler with categorization
  - Integrates with `SmartSorter` for intelligent document routing
  - Template-based path generation with placeholders

- **`zone_manager.py`** (Python 3.9+):
  - `ZoneManager`: Manages dropzone configurations
  - Thread-safe CRUD operations for zones
  - Persistence to `~/.config/folder_extractor/zones.json`
  - Configuration includes: path, enabled status, auto_sort, categories, path templates

- **`smart_sorter.py`** (Python 3.9+):
  - `SmartSorter`: AI-powered document categorization orchestrator
  - Uses Gemini AI for content analysis and entity extraction
  - Integrates with `KnowledgeGraph` for metadata storage
  - Returns structured categorization (category, sender, year, entities)

- **`ai_async.py`** (Python 3.9+):
  - `IAIClient`: Interface for AI clients
  - `AsyncGeminiClient`: Async client for Google Gemini API
  - File upload and analysis capabilities

- **`ai_resilience.py`** (Python 3.9+):
  - Resilience patterns for AI operations
  - Exponential backoff retry logic
  - Rate limiting and quota management

- **`ai_prompts.py`** (Python 3.9+):
  - `get_system_prompt()`: Generates system prompts for AI categorization
  - Configurable category templates

- **`preprocessor.py`** (Python 3.9+):
  - Document preprocessing for AI analysis
  - Text extraction from various formats

- **`security.py`** (Python 3.9+):
  - Security utilities for AI operations
  - Input sanitization and validation

- **`memory/graph.py`** (Python 3.9+):
  - `IKnowledgeGraph`: Interface for knowledge graph
  - `KnowledgeGraph`: Graph-based storage using KùzuDB
  - Document metadata, entity storage, and relationship tracking
  - Natural language to Cypher query translation
  - Thread-safe operations with connection pooling

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

### 5. API Layer (`api/`) - Python 3.9+

**Purpose**: Expose core functionality via REST API and WebSockets for native macOS integration

- **`server.py`**: FastAPI application factory with lifecycle management
  - `create_app()`: Creates configured FastAPI instance
  - CORS configuration for localhost
  - Lifespan events for resource management

- **`endpoints.py`**: REST endpoint implementations
  - `GET /health`: Health check endpoint
  - `POST /api/v1/process`: Process a single file
  - `GET /api/v1/zones`: List all dropzones
  - `POST /api/v1/zones`: Create new dropzone
  - `DELETE /api/v1/zones/{zone_id}`: Delete dropzone
  - `POST /api/v1/watcher/start`: Start watching a zone
  - `POST /api/v1/watcher/stop`: Stop watching a zone
  - `GET /api/v1/watcher/status`: Get watcher status

- **`websocket.py`**: WebSocket connection manager
  - `ConnectionManager`: Manages active WebSocket connections
  - Bidirectional communication for chat and status updates
  - Broadcast capabilities for real-time notifications

- **`models.py`**: Pydantic models for request/response validation
  - Request models: `ProcessRequest`, `ZoneConfig`, `WatcherStartRequest`, `WatcherStopRequest`
  - Response models: `ProcessResponse`, `ZoneResponse`, `WatcherStatusResponse`, `HealthResponse`
  - WebSocket models: `WebSocketMessage`

- **`dependencies.py`**: FastAPI dependency injection functions
  - `get_zone_manager()`: Provides singleton ZoneManager
  - `get_smart_sorter()`: Provides SmartSorter instance (optional, requires AI config)
  - `get_knowledge_graph()`: Provides KnowledgeGraph instance

**Design Principle**: The API layer is a **thin adapter** that delegates to existing core components:
- No business logic in API layer
- Direct reuse of `EnhancedExtractionOrchestrator`, `SmartSorter`, `FolderEventHandler`
- Follows existing Dependency Injection pattern

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
Settings, state manager, and zone manager use singleton pattern for global access:
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

File system watching with event-driven architecture:
```python
class FolderEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        # React to file creation events
```

### 7. **Adapter Pattern**
Migration adapters provide compatibility:
```python
class ExtractorAdapter(IExtractor):
    def __init__(self, enhanced_extractor: IEnhancedExtractor):
        self.enhanced_extractor = enhanced_extractor
```

### 8. **Strategy Pattern**
Different archive handlers implement common interface:
```python
class ZipArchiveHandler(IArchiveHandler):
    def extract(self, archive_path: Path, target_dir: Path) -> None:
        # ZIP-specific extraction
```

### 9. **Repository Pattern**
Knowledge graph abstracts data persistence:
```python
class KnowledgeGraph(IKnowledgeGraph):
    def ingest(self, file_info: dict) -> None:
        # Abstract storage details
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

### CLI Mode (Traditional Extraction)

1. **User Input** → CLI Parser → Settings Configuration
2. **Execution Request** → CLI App → Orchestrator
3. **File Discovery** → FileDiscovery finds files based on criteria
4. **Archive Extraction** (if `--extract-archives`) → Extract ZIP/TAR safely
5. **Validation** → Security and file validators check each file
6. **Hash Indexing** (if global-dedup) → Build index of existing files
7. **File Operations** → FileMover moves files with deduplication checks
8. **State Updates** → StateManager tracks operation progress
9. **Progress Display** → ConsoleInterface shows real-time progress
10. **History Saving** → HistoryManager saves operations for undo
11. **Cleanup** → Remove empty directories
12. **Result Display** → ConsoleInterface shows summary with duplicate counts

### API/Watch Mode (Automatic Processing)

1. **File System Event** → Watchdog detects file creation
2. **Stability Check** → StabilityMonitor ensures file is complete
3. **AI Analysis** → SmartSorter categorizes document (category, sender, year, entities)
4. **Template Expansion** → Path template with placeholders resolved
5. **File Move** → File moved to categorized location
6. **Metadata Storage** → KnowledgeGraph stores document metadata and entities
7. **WebSocket Notification** → Real-time update sent to connected clients
8. **History Saved** → Operation recorded for undo capability

## Thread Safety

The application ensures thread safety through:

1. **Thread-safe State Manager**: Uses locks for concurrent access
2. **Thread-safe Zone Manager**: Locks for configuration updates
3. **Abort Signal**: Threading.Event for safe operation cancellation
4. **Atomic Operations**: File operations are atomic where possible
5. **Progress Callbacks**: Thread-safe progress reporting
6. **Connection Manager**: Thread-safe WebSocket connection handling

## Security Architecture

### Path Traversal Protection

1. **Safe Directory Validation**: Operations only in Desktop/Downloads/Documents
2. **Zip Slip Prevention**: Archive extraction validates all paths stay within target
3. **Path Canonicalization**: Resolves symlinks and normalizes paths before validation
4. **Absolute Path Rejection**: Archives with absolute paths are rejected

### Archive Security (Zip Slip Protection)

```python
def _is_safe_path(member_path: Path, target_dir: Path) -> bool:
    # Resolve to absolute paths
    resolved_member = member_path.resolve()
    resolved_target = target_dir.resolve()

    # Check if member is within target
    return resolved_member.is_relative_to(resolved_target)
```

**Protection Layers:**
1. Pre-extraction path validation
2. Post-extraction path verification
3. Rejection of absolute paths in archives
4. Symlink resolution to prevent escapes

### Input Validation

1. **File Type Validation**: Whitelist-based file extension checking
2. **Domain Validation**: URL domain parsing with subdomain support
3. **Depth Validation**: Numeric bounds checking
4. **Path Sanitization**: Removes dangerous characters and patterns

## Migration Strategy

The architecture maintains backward compatibility:

1. **Legacy Function Names**: `main.py` provides wrapper functions with original German names
2. **History Migration**: Automatic migration from local `.folder_extractor_history.json` to central config
3. **Interface Adapters**: Bridge between legacy and enhanced interfaces

## Testing Strategy

The modular architecture enables comprehensive testing:

1. **Unit Tests**: Test each component in isolation (`tests/unit/`)
   - Component-specific tests for all core modules
   - API-specific tests in `tests/unit/api/`
2. **Integration Tests**: Test component interactions (`tests/integration/`)
   - End-to-end extraction workflows
   - Archive extraction scenarios
   - Smart sorting integration
   - Watch mode integration
3. **Security Tests**: Security-focused test scenarios
   - Zip Slip attack prevention
   - Path traversal attempts
   - Input validation edge cases
4. **Performance Tests**: Benchmark critical operations (`tests/performance/`)
   - Deep directory structure handling (1500+ levels)
   - Large file set processing
   - Hash indexing performance
5. **Property Tests**: Hypothesis-based testing (`test_properties.py`)
   - Generative testing for edge cases

**Coverage Target**: 90%+ (some AI/API modules excluded on Python 3.8, see `pyproject.toml`)

## Extension Points

The architecture is designed for extensibility:

1. **New File Discovery Strategies**: Implement `IFileDiscovery`
2. **Custom File Operations**: Implement `IFileOperations`
3. **Alternative UI**: Implement `IConsoleInterface`
4. **State Persistence**: Extend `IStateManager`
5. **Progress Visualization**: Extend `IProgressTracker`
6. **Archive Formats**: Implement `IArchiveHandler` for RAR, 7z, etc.
7. **AI Providers**: Implement `IAIClient` for OpenAI, Claude, etc.
8. **Storage Backends**: Implement `IKnowledgeGraph` for Neo4j, PostgreSQL, etc.

## Performance Considerations

1. **Lazy Loading**: Components loaded only when needed
2. **Efficient File Walking**: Single pass through directory tree
3. **Batch Operations**: Progress updates batched for efficiency
4. **Memory Efficiency**: Stream processing for large file sets
5. **Iterative File Discovery**: `os.walk()` instead of recursion prevents stack overflow
6. **Early Pruning**: `dirs[:] = []` pattern stops traversal at depth/hidden boundaries
7. **Depth Calculation Optimization**: Uses `len(path.parts)` instead of `resolve()` (line 91)
8. **Hash Index Optimization**: Size-based pre-filtering before expensive hash calculation
9. **Chunked File Reading**: 8KB chunks for hash calculation
10. **AI Caching**: Knowledge graph caches document metadata to reduce API calls
11. **Connection Pooling**: Database connection pooling in KnowledgeGraph

## Dependencies

### Runtime Dependencies

**CLI Mode (Python 3.8+)**:
- `rich>=13.0.0` - Enhanced terminal output (progress bars, tables, colors)

**API/AI Mode (Python 3.9+, optional)**:
- `fastapi` - REST API framework
- `uvicorn[standard]` - ASGI server
- `pydantic>=2.0.0` - Data validation
- `websockets` - WebSocket support
- `python-dotenv` - Environment configuration
- `google-generativeai` - Gemini AI client
- `watchdog` - File system monitoring
- `kuzu` - Graph database (KùzuDB)

### Development Dependencies

- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `pytest-benchmark>=4.0` - Performance benchmarking
- `pytest-xdist>=3.0` - Parallel test execution
- `hypothesis>=6.0` - Property-based testing

## Python Version Compatibility

- **Python 3.8**: CLI mode with all core features (extraction, deduplication, sorting, archives)
- **Python 3.9+**: Full feature set including AI sorting, watch mode, and REST API
  - AI modules require `google-generativeai` which only supports Python 3.9+
  - These modules are excluded from coverage on Python 3.8 (see `pyproject.toml`)

## Implemented Features (Previously "Future Enhancements")

The following features have been implemented since the initial architecture:

1. ✅ **Archive Extraction**: Safe ZIP/TAR extraction with Zip Slip protection (`--extract-archives`)
2. ✅ **Watch Mode**: Monitor directories and auto-organize new files (API mode)
3. ✅ **AI-Powered Sorting**: Gemini-based document categorization with entity extraction
4. ✅ **Knowledge Graph**: Graph-based metadata storage using KùzuDB
5. ✅ **REST API**: Full FastAPI implementation with WebSocket support
6. ✅ **Dropzone Management**: Multi-zone configuration with templates
7. ✅ **Real-time Notifications**: WebSocket-based status updates

## Future Enhancements

The modular architecture enables future enhancements:

1. **Persistent Configuration**: Save user preferences to config file (planned for v1.5.0)
2. **Improved Undo for Duplicates**: Restore deduplicated files by copying (planned for v1.5.0)
3. **GUI Frontend**: Desktop application using the same core (Electron/Tauri)
4. **Additional Archive Formats**: RAR, 7z support via `IArchiveHandler`
5. **EXIF-based Sorting**: Organize photos by capture date
6. **Plugin System**: Dynamic loading of extensions
7. **Multi-language Support**: Internationalization (i18n)
8. **Alternative AI Providers**: OpenAI, Claude, local models via `IAIClient`
9. **Advanced Search**: Natural language queries via KnowledgeGraph
10. **Batch Operations API**: Process multiple files in single request
