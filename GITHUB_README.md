# Folder Extractor 🗂️

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-D7FF64.svg)](https://github.com/astral-sh/ruff)

A **secure command-line tool** for extracting files from subdirectories into the current folder. Perfect for cleaning up deeply nested folder structures.

## 🚀 Features

- **🔒 Security**: Only runs in Desktop, Downloads, or Documents folders
- **📁 Smart Duplicate Handling**: Automatic renaming for duplicate files
- **🎯 Depth Control**: Specify how deep to search in folder structure
- **🧹 Auto-Cleanup**: Removes empty folders after moving files
- **📊 Detailed Feedback**: Shows each step and final summary
- **✅ User Confirmation**: Preview and confirmation before execution
- **🛑 ESC Key Abort**: Safe cancellation at any time
- **↩️ Undo Function**: Revert the last operation
- **🔍 Dry-Run Mode**: Preview what would happen without doing it
- **📈 Progress Display**: Percentage progress during operations
- **📎 File Type Filter**: Extract only specific file types
- **🌐 Domain Filter**: Filter web links by domain
- **🗂️ Sort by Type**: Organize files automatically into type folders
- **👻 Hidden Files**: Optionally include hidden files

## 📦 Installation

### System-wide installation via pip

```bash
# In the project directory:
pip install .

# Or for development (editable installation):
pip install -e .
```

After installation, the `folder-extractor` command is available system-wide!

### Alternative: Direct usage without installation

```bash
python folder_extractor.py [options]
```

## 💻 Usage

```bash
# Standard: Unlimited depth
folder-extractor

# Maximum 3 levels deep
folder-extractor --depth 3

# Only first level
folder-extractor --depth 1

# Preview without actual moving
folder-extractor --dry-run

# Undo last operation
folder-extractor --undo

# Show version
folder-extractor --version

# Extract only PDFs (folder structure remains)
folder-extractor --type pdf

# Multiple file types
folder-extractor --type pdf,doc,docx

# Extract images from max 2 levels
folder-extractor --type jpg,png,gif --depth 2

# Extract only YouTube links
folder-extractor --type url,webloc --domain youtube.com

# Links from multiple domains
folder-extractor --type url --domain youtube.com,github.com,reddit.com

# Sort files by type
folder-extractor --sort-by-type

# Include hidden files
folder-extractor --include-hidden

# Combined: Extract hidden PDFs sorted
folder-extractor --type pdf --include-hidden --sort-by-type
```

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [README.md](README.md) - Complete German documentation

## 🔧 Development

### Requirements

- Python 3.7+
- macOS, Linux, or Windows
- No external dependencies

### Running Tests

```bash
python -m pytest tests/

# Run specific test
python -m pytest tests/unit/test_core_extractor.py

# Run with coverage
python -m pytest --cov=folder_extractor tests/
```

### Project Structure

```
folder_extractor/
├── cli/                  # Command Line Interface
├── core/                 # Business Logic
├── config/               # Configuration
├── utils/                # Utilities
└── main_final.py         # Main entry point
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Future Enhancements

- GUI frontend using the same core
- Network operations for remote file systems
- Plugin system for dynamic extensions
- Parallel processing for file operations
- Cloud storage provider support

## 📞 Contact

For questions or suggestions, please open an issue or contact the maintainer.

---

**Folder Extractor** - Making file organization simple and secure! 🚀