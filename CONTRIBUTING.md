# Contributing to Folder Extractor

Thank you for your interest in contributing to Folder Extractor! We welcome contributions from everyone.

**Repository**: https://github.com/0ui-labs/folder-extractor

## 🤝 Ways to Contribute

- **Bug Reports**: Report bugs by opening issues
- **Feature Requests**: Suggest new features
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve documentation
- **Tests**: Add more test cases
- **Translations**: Help with internationalization

## 📋 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/folder-extractor.git
cd folder-extractor
```

### 2. Install Development Dependencies

```bash
# Install with test dependencies
pip install -e ".[test]"

# Verify installation
folder-extractor --version
```

### 3. Run Tests

```bash
# Run all tests
python run_tests.py

# Or with pytest directly
pytest tests/

# With coverage report
python run_tests.py coverage
```

### 4. Run Linting

```bash
# Check for issues
ruff check .

# Auto-format code
ruff format .
```

## 🔧 Development Workflow

### Branch Strategy

- `main`: Stable production code (protected)
- `feature/*`: Feature development branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Critical production fixes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

<body>

<footer>
```

**Types**:
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style changes (formatting) |
| `refactor` | Code refactoring |
| `perf` | Performance improvements |
| `test` | Adding or modifying tests |
| `chore` | Build process or tooling changes |

**Examples**:
```bash
feat(core): add global deduplication with hash index
fix(cli): correct progress percentage for large files
docs(readme): add deduplicate option examples
test(hashing): add SHA256 calculation tests
refactor(extractor): extract file operations to separate module
```

### Pull Request Process

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit with clear messages

3. **Run tests** to ensure nothing breaks:
   ```bash
   python run_tests.py
   ```

4. **Run linting** to maintain code quality:
   ```bash
   ruff check .
   ruff format .
   ```

5. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request** against the `main` branch

7. **CodeRabbit will automatically review** your PR with AI-powered analysis

8. **Address feedback** from CodeRabbit and human reviewers

9. **Merge** once all checks pass and approvals are obtained

## 🤖 CodeRabbit Integration

All pull requests are automatically reviewed by CodeRabbit:

- 🔍 **Code Analysis**: AI-powered review of your changes
- 🔐 **Security Checks**: Vulnerability detection
- ⚡ **Performance**: Optimization suggestions
- 📝 **Style**: PEP 8 and best practices

You can interact with CodeRabbit in PR comments:
```markdown
@coderabbitai explain this function
@coderabbitai is there a security issue here?
@coderabbitai review again
```

## 📚 Code Style

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- Use **Ruff** for formatting and linting (automatically enforced)
- Ruff combines Black-compatible formatting with comprehensive linting

### Type Hints

```python
from typing import Optional, List, Dict
from pathlib import Path

def find_files(
    directory: Path,
    max_depth: int = 0,
    file_types: Optional[List[str]] = None,
) -> List[Path]:
    """Find files in directory."""
    ...
```

### Documentation

Use **Google-style docstrings**:

```python
def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate SHA256 hash of a file.

    Reads the file in chunks for memory efficiency with large files.

    Args:
        file_path: Path to the file to hash.
        chunk_size: Size of chunks to read (default: 8KB).

    Returns:
        Hexadecimal string of the SHA256 hash.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.

    Examples:
        >>> calculate_file_hash(Path("document.pdf"))
        'a1b2c3d4e5f6...'
    """
```

## 🧪 Testing

### Test Structure

```
tests/
├── unit/                    # Unit tests (538+ tests)
│   ├── test_cli_*.py        # CLI layer tests
│   ├── test_core_*.py       # Core logic tests
│   ├── test_hashing.py      # Hash calculation tests
│   ├── test_global_dedup.py # Deduplication tests
│   └── test_properties.py   # Property-based tests (Hypothesis)
├── integration/             # End-to-end workflow tests
│   ├── test_extraction_workflow.py
│   └── test_backward_compatibility.py
└── performance/             # Benchmark tests
    └── test_benchmarks.py
```

### Running Tests

```bash
# All tests
python run_tests.py

# Specific category
pytest tests/unit/
pytest tests/integration/

# Specific test file
pytest tests/unit/test_hashing.py

# With coverage (target: 95%+)
python run_tests.py coverage

# Verbose output
pytest -v tests/

# Run only failing tests
pytest --lf
```

### Writing Tests

```python
import pytest
from pathlib import Path
from folder_extractor.core.file_operations import FileOperations

class TestFileOperations:
    """Tests for FileOperations class."""

    def test_calculate_hash_returns_consistent_result(self, tmp_path: Path):
        """Hash of same content should always be identical."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        ops = FileOperations()

        # Act
        hash1 = ops.calculate_file_hash(test_file)
        hash2 = ops.calculate_file_hash(test_file)

        # Assert
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
```

### Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_unique_name_always_unique(self, filename: str):
    """Generated names should never collide."""
    # ...
```

## 🎯 Architecture Guidelines

### Module Structure

```
folder_extractor/
├── cli/           # User interface layer
│   ├── app.py     # Main CLI application
│   ├── parser.py  # Argument parsing
│   └── interface.py # Console I/O
├── core/          # Business logic layer
│   ├── extractor.py      # Extraction orchestration
│   ├── file_discovery.py # File finding
│   ├── file_operations.py # Move, hash, dedupe
│   └── state_manager.py  # Thread-safe state
├── config/        # Configuration layer
│   ├── constants.py # Messages, mappings
│   └── settings.py  # Runtime settings
└── utils/         # Shared utilities
    ├── path_validators.py
    ├── file_validators.py
    └── parsers.py
```

### Key Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Interface-based Design**: Use abstract base classes for contracts
3. **Dependency Injection**: Pass dependencies through constructors
4. **Thread Safety**: Use locks and Events for concurrent operations
5. **Backward Compatibility**: Maintain legacy function names in `main.py`

### Adding New Features

1. **Check FEATURES.md** for planned features
2. **Define Interfaces** first in the appropriate module
3. **Implement** the concrete classes
4. **Add Tests** (aim for 95%+ coverage)
5. **Update Documentation**:
   - ARCHITECTURE.md for technical changes
   - README.md for user-facing features
   - CHANGELOG.md for version history
6. **Integrate** with existing components

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | German technical documentation |
| `README_DE.md` | German marketing-style README |
| `README_V2.md` | English marketing-style README |
| `ANLEITUNG.md` | German user guide with examples |
| `ARCHITECTURE.md` | Technical architecture documentation |
| `CHANGELOG.md` | Version history |
| `FEATURES.md` | Roadmap and planned features |
| `CLAUDE.md` | AI assistant context |
| `CODE_OF_CONDUCT.md` | Community standards (Contributor Covenant 2.1) |

## 🔒 Security

When contributing security-related code:

- Never hardcode secrets or credentials
- Validate all user input
- Use parameterized queries (if applicable)
- Follow the principle of least privilege
- Report security vulnerabilities privately

## 🤔 Need Help?

- **Issues**: Check existing issues or open a new one
- **Discussions**: Use GitHub Discussions for questions
- **CodeRabbit**: Ask `@coderabbitai` in any PR comment
- **Documentation**: See ARCHITECTURE.md for technical details

## 🙏 Thank You!

Your contributions help make Folder Extractor better for everyone! 🎉

---

**Repository**: https://github.com/0ui-labs/folder-extractor
