# Contributing to Folder Extractor

Thank you for your interest in contributing to Folder Extractor! We welcome contributions from everyone.

## 🤝 Ways to Contribute

- **Bug Reports**: Report bugs by opening issues
- **Feature Requests**: Suggest new features
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve documentation
- **Tests**: Add more test cases
- **Translations**: Help with internationalization

## 📋 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/folder-extractor.git
   cd folder-extractor
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## 🔧 Development Workflow

### Branch Strategy

- `main`: Stable production code
- `develop`: Integration branch for features
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
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `chore`: Build process or auxiliary tool changes

**Examples**:
```
feat(extractor): add domain filtering for web links
fix(interface): correct progress percentage calculation
docs(readme): update installation instructions
test(extractor): add tests for duplicate file handling
```

### Pull Request Process

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit them with clear messages

3. **Run tests** to ensure nothing breaks:
   ```bash
   python -m pytest tests/
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

6. **Open a Pull Request** against the `develop` branch

7. **Wait for review** and address any feedback

## 📚 Code Style

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- Use **Ruff** for code formatting and linting (automatically enforced)
- Ruff combines formatting (Black-compatible) and linting (Flake8, isort, and more) in one tool

### Type Hints

- Use type hints for all functions and methods
- Use `Optional` for nullable parameters
- Use `Any` sparingly

### Documentation

- Use **Google-style docstrings** for all public functions and classes
- Keep docstrings up-to-date
- Document all parameters and return values

### Testing

- Write tests for new features
- Maintain >90% code coverage
- Use descriptive test names
- Test edge cases and error conditions

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/unit/test_core_extractor.py

# Run with coverage
python -m pytest --cov=folder_extractor tests/

# Run with verbose output
python -m pytest -v tests/
```

### Test Structure

```
tests/
├── unit/          # Unit tests for individual components
├── integration/   # Integration tests for component interactions
└── performance/   # Performance and benchmark tests
```

## 🎯 Architecture Guidelines

### Key Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Interface-based Design**: Use abstract base classes for contracts
3. **Dependency Injection**: Pass dependencies through constructors
4. **Thread Safety**: Ensure thread-safe operations where needed
5. **Backward Compatibility**: Maintain compatibility with existing code

### Adding New Features

1. **Define Interfaces** first in the appropriate module
2. **Implement** the concrete classes
3. **Add Tests** for the new functionality
4. **Update Documentation** in ARCHITECTURE.md
5. **Integrate** with existing components

## 📖 Documentation

### Updating Documentation

- **ARCHITECTURE.md**: Update for architectural changes
- **README.md**: Update for user-facing changes
- **GITHUB_README.md**: Update for GitHub-specific content
- **CHANGELOG.md**: Add entries for new versions

### Docstring Format

```python
def function_name(param1: type, param2: type) -> return_type:
    """Brief description of the function.
    
    Detailed description explaining what the function does,
    when to use it, and any important considerations.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: Description of when this exception is raised
        
    Examples:
        >>> function_name(value1, value2)
        expected_result
    """
    # Function implementation
```

## 🤔 Need Help?

If you have questions about contributing:

- Check existing issues and pull requests
- Ask in the discussions section
- Contact the maintainers

## 🙏 Thank You!

Your contributions help make Folder Extractor better for everyone! 🎉