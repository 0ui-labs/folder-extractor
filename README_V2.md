# 🗂️ Folder Extractor

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-D7FF64.svg)](https://github.com/astral-sh/ruff)
[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)](CHANGELOG.md)

> **🇩🇪 Deutsche Version:** Hier klicken für die [deutsche Dokumentation](README_DE.md).

> **Declutter without fear.** The intelligent CLI tool to extract, sort, and organize files from deeply nested directory structures – now with AI-powered smart sorting.

Folder Extractor hoists files from subdirectories into your current directory ("flattening"), sorts them by type if requested, and cleans up empty folders. It was built with one primary goal: **Safety.**

---

## ✨ Why Folder Extractor?

Most scripts of this kind are "quick & dirty" and risky. Folder Extractor is different:

*   🛡️ **Safety First:** Restricts operations to safe directories **only** (Desktop, Downloads, Documents). Prevents accidental system damage.
*   ↩️ **Time Machine:** Includes a full **Undo** function. Made a mistake? Revert everything with one command.
*   🧠 **Intelligent:** Detects duplicates and auto-renames them (`file_1.txt`) instead of overwriting data.
*   🔄 **Smart Dedup:** Detects identical files by content (SHA256 hash) – no more duplicate copies.
*   🤖 **AI-Powered:** Automatically categorize documents with Google Gemini (Python 3.9+).
*   👁️ **Auto-Organize:** Watch mode monitors folders and processes files automatically.
*   📦 **Archive Support:** Safely extracts ZIP/TAR archives with Zip Slip protection.

## 🚀 Quick Start

### Installation

```bash
# Basic CLI mode (Python 3.8+)
pip install .

# With AI features (Python 3.9+)
pip install fastapi uvicorn[standard] google-generativeai watchdog
```

### Usage

```bash
# Run interactive mode
folder-extractor

# Or automate specific tasks
folder-extractor --sort-by-type --depth 2

# AI-powered organization (Python 3.9+)
folder-extractor --watch --sort-by-type

# Extract and organize archives
folder-extractor --extract-archives --sort-by-type
```

---

## 💡 Use Cases

### 1. Eliminate Chaos ("Flattening")
You have a folder with 50 subfolders, but you want all files in one place?
```bash
folder-extractor
```
*Moves all files from subdirectories to the root and removes the empty shells.*

### 2. Organize Downloads
Clean up your downloads folder and sort files into categories (PDF, JPG, DOCX...) instantly?
```bash
folder-extractor --sort-by-type
```
*Creates folders like `PDF/`, `JPEG/`, `VIDEO/` and sorts files automatically.*

### 3. Extract Archives Safely
Need to unpack multiple ZIP/TAR files and organize the contents?
```bash
folder-extractor --extract-archives --sort-by-type
```
*Safely extracts archives with Zip Slip protection and organizes all files by type.*

### 4. Auto-Organize Downloads (Python 3.9+)
Want your downloads folder to organize itself automatically?
```bash
cd ~/Downloads
folder-extractor --watch --sort-by-type --extract-archives
```
*Monitors the folder and automatically processes new files as they arrive.*

### 5. AI Document Categorization (Python 3.9+)
Let AI organize your documents into smart categories?
```bash
export GEMINI_API_KEY=your-key
folder-extractor --watch --sort-by-type
```
*AI analyzes documents and sorts them into Finance/, Contracts/, Insurance/, etc.*

### 6. Targeted Extraction
Need only the PDFs from a deep project archive?
```bash
folder-extractor --type pdf --depth 3
```
*Extracts only `.pdf` files, max 3 levels deep. Everything else stays untouched.*

### 7. Clean up Link Collections
Collecting YouTube links from various `.url` or `.webloc` files?
```bash
folder-extractor --type url,webloc --domain youtube.com
```
*Filters web bookmarks by domain and extracts only matching links.*

### 8. Eliminate Duplicates
You have the same photos in 10 different folders?
```bash
folder-extractor --deduplicate --global-dedup
```
*Detects identical files by content and keeps only one copy.*

### 9. Ask Your Documents (Python 3.9+)
Want to query your document collection in natural language?
```bash
folder-extractor --ask "Which insurance documents do I have from 2024?"
```
*Knowledge Graph allows natural language queries across your organized files.*

### 10. "Oops, I didn't mean to do that!"
Did you extract files that should have stayed where they were?
```bash
folder-extractor --undo
```
*Restores the previous state completely.*

---

## 🛠️ Command Reference

### Core Options

| Option | Description |
|--------|-------------|
| `--dry-run`, `-n` | **Preview.** Shows what would happen without making changes. |
| `--undo`, `-u` | Reverts the last operation in the current directory. |
| `--sort-by-type`, `-s` | Sorts extracted files into subfolders based on file type. |
| `--depth`, `-d` | Maximum search depth (0 = unlimited). |
| `--type`, `-t` | Filters by file extension (e.g., `pdf,jpg`). |
| `--domain` | Filters web links by domain (only for `.url`/`.webloc`). |
| `--include-hidden` | Includes hidden files (starting with `.`). |
| `--deduplicate` | Detects identical files (hash comparison) and avoids duplicates. |
| `--global-dedup` | Global duplicate check across entire target folder. |

### Archive Options

| Option | Description |
|--------|-------------|
| `--extract-archives` | Safely extract ZIP, TAR, TAR.GZ, TGZ archives. |
| `--delete-archives` | Delete archive files after successful extraction. |

### Advanced Options (Python 3.9+)

| Option | Description |
|--------|-------------|
| `--watch` | Monitor folder and automatically process new files. |
| `--ask` | Query your documents with natural language. |

### Other

| Option | Description |
|--------|-------------|
| `--version`, `-v` | Shows the installed version. |
| `--help`, `-h` | Shows help message. |

---

## 🔒 Safety Concept

To prevent data loss, Folder Extractor enforces strict rules:

1.  **Whitelist Paths:** Operations are denied unless executed within `~/Desktop`, `~/Downloads`, or `~/Documents`.
2.  **System Protection:** Automatically ignores system files like `.DS_Store`, `Thumbs.db`, and `.git` directories.
3.  **No Overwriting:** If `file.txt` exists, the new file becomes `file_1.txt`. Data is **never** overwritten.
4.  **Confirmation:** You must explicitly confirm before any destructive action starts (except in Undo mode).
5.  **Zip Slip Protection:** All archive extractions validate paths to prevent path traversal attacks.
6.  **Atomic Operations:** Uses atomic file operations to prevent data corruption.

---

## 🌐 REST API Server (Python 3.9+)

Folder Extractor includes a FastAPI-based REST API for integration with native macOS/iOS apps:

```bash
# Start API server
folder-extractor-api

# Custom configuration
folder-extractor-api --port 8000 --reload
```

**Available at:** `http://localhost:23456/docs`

**Features:**
- 8 REST endpoints for file processing and dropzone management
- WebSocket support for real-time updates
- Native Swift integration examples included
- Automatic file monitoring and processing

See [full documentation](README.md#-rest-api-server-python-39) for API details.

---

## 📦 Features at a Glance

### Core Features (Python 3.8+)
✅ Safe directory restrictions
✅ Content-based deduplication (SHA256)
✅ Flexible depth control
✅ Sort by file type
✅ File type filters
✅ Domain filtering for web links
✅ Archive extraction (ZIP/TAR)
✅ Global duplicate detection
✅ Hidden file support
✅ Auto cleanup empty folders
✅ Full undo capability
✅ Dry-run preview mode
✅ Rich terminal progress display

### Advanced Features (Python 3.9+)
🤖 AI-powered document categorization
👁️ Watch mode with auto-processing
🧠 Knowledge Graph with natural language queries
🌐 REST API with WebSocket support
📱 Native macOS/iOS integration

---

## 💻 Development

Contributions are welcome! The project is modular and extensively tested.

```bash
# Setup development environment
pip install -e ".[test]"

# Run tests
python run_tests.py

# With coverage
python run_tests.py coverage

# Linting & formatting
ruff check .
ruff format .

# Type checking
pyright
```

**Coverage target:** 90%+

For detailed architectural information, please check [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 📖 Documentation

- **[README.md](README.md)** - Full technical documentation (English)
- **[README_DE.md](README_DE.md)** - Vollständige Dokumentation (Deutsch)
- **[ANLEITUNG.md](ANLEITUNG.md)** - Ausführliche Bedienungsanleitung (Deutsch)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture documentation and design patterns
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for Claude Code

---

## 🙏 Credits

- Developed by **Philipp Briese**
- AI Integration: Google Gemini 3 Flash Preview
- Graph Database: KùzuDB
- Terminal UI: Rich Library
- Web Framework: FastAPI

---

## 📄 License

MIT License - Copyright (c) 2024-2026 Philipp Briese

See [LICENSE](LICENSE) file for details.

---

**Happy organizing!** 🗂️

*Made with ❤️ and Python.*
