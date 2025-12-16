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
├── main.py               # Legacy monolithic implementation (preserved for compatibility)
├── main_enhanced.py      # Enhanced entry point with architecture selection
├── main_final.py         # Final integrated entry point
│
├── cli/                  # Command Line Interface layer
│   ├── __init__.py
│   ├── parser.py         # Argument parsing
│   ├── interface.py      # Console interaction & progress display
│   ├── app.py           # CLI application orchestration
│   └── app_v2.py        # Enhanced CLI with state management
│
├── core/                 # Business logic layer
│   ├── __init__.py
│   ├── file_discovery.py # File finding and filtering
│   ├── file_operations.py # File manipulation operations
│   ├── extractor.py      # Core extraction orchestration
│   ├── extractor_v2.py   # Enhanced extractor with state management
│   ├── state.py          # Application state interfaces
│   ├── state_manager.py  # Thread-safe state management
│   ├── progress.py       # Progress tracking
│   └── migration.py      # Migration utilities and adapters
│
├── config/              # Configuration layer
│   ├── __init__.py
│   ├── constants.py     # Application constants
│   └── settings.py      # Runtime settings management
│
└── utils/               # Utility functions
    ├── __init__.py
    ├── path_validators.py  # Path security validation
    ├── file_validators.py  # File validation utilities
    └── terminal.py         # Terminal operations
```

## Key Components

### 1. CLI Layer (`cli/`)

**Purpose**: Handle user interaction, command parsing, and presentation

- **`parser.py`**: Defines command-line arguments using argparse
- **`interface.py`**: 
  - `ConsoleInterface`: Manages user output and input
  - `KeyboardHandler`: Handles ESC key detection for abort
- **`app.py`**: Basic CLI application orchestration
- **`app_v2.py`**: Enhanced CLI with integrated state management

### 2. Core Business Logic (`core/`)

**Purpose**: Implement the actual file extraction logic

- **`file_discovery.py`**:
  - `IFileDiscovery`: Interface for file discovery
  - `FileDiscovery`: Finds files based on criteria (depth, type, hidden)
  
- **`file_operations.py`**:
  - `IFileOperations`: Interface for file operations
  - `FileOperations`: Basic file operations (move, copy, unique naming)
  - `FileMover`: High-level file moving with progress tracking
  - `HistoryManager`: Manages operation history for undo

- **`extractor.py`**:
  - `IExtractor`: Interface for extraction operations
  - `FileExtractor`: Coordinates file discovery and moving
  - `ExtractionOrchestrator`: High-level extraction workflow

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

- **`path_validators.py`**: Security validation for paths
- **`file_validators.py`**: File type and attribute validation
- **`terminal.py`**: Terminal settings and color support

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

## Data Flow

1. **User Input** → CLI Parser → Settings Configuration
2. **Execution Request** → CLI App → Orchestrator
3. **File Discovery** → FileDiscovery finds files based on criteria
4. **Validation** → Security and file validators check each file
5. **File Operations** → FileMover moves files with progress tracking
6. **State Updates** → StateManager tracks operation progress
7. **Progress Display** → ConsoleInterface shows real-time progress
8. **History Saving** → HistoryManager saves operations for undo
9. **Result Display** → ConsoleInterface shows summary

## Thread Safety

The application ensures thread safety through:

1. **Thread-safe State Manager**: Uses locks for concurrent access
2. **Abort Signal**: Threading.Event for safe operation cancellation
3. **Atomic Operations**: File operations are atomic where possible
4. **Progress Callbacks**: Thread-safe progress reporting

## Migration Strategy

The architecture supports gradual migration from the monolithic design:

1. **Backward Compatibility**: Legacy main.py preserved
2. **Architecture Selection**: Environment variable controls which architecture to use
3. **Adapters**: Bridge between old and new interfaces
4. **Settings Migration**: Automatic migration of settings to state manager

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

## Security Considerations

1. **Path Validation**: Only operates in safe user directories
2. **No Code Execution**: No dynamic code execution
3. **Input Sanitization**: All user input validated
4. **Atomic Operations**: Prevent partial state corruption

## Future Enhancements

The modular architecture enables future enhancements:

1. **GUI Frontend**: Add graphical interface using the same core
2. **Network Operations**: Add remote file system support
3. **Plugin System**: Dynamic loading of extensions
4. **Parallel Processing**: Multi-threaded file operations
5. **Cloud Integration**: Support for cloud storage providers