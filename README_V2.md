# 🗂️ Folder Extractor

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-D7FF64.svg)](https://github.com/astral-sh/ruff)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-none-success)](requirements.txt)

> **🇩🇪 Deutsche Version:** Hier klicken für die [deutsche Dokumentation](README.de.md).

> **Declutter without fear.** The safe CLI tool to extract, sort, and organize files from deeply nested directory structures.

Folder Extractor hoists files from subdirectories into your current directory ("flattening"), sorts them by type if requested, and cleans up empty folders. It was built with one primary goal: **Safety.**

---

## ✨ Why Folder Extractor?

Most scripts of this kind are "quick & dirty" and risky. Folder Extractor is different:

*   🛡️ **Safety First:** Restricts operations to safe directories **only** (Desktop, Downloads, Documents). Prevents accidental system damage.
*   ↩️ **Time Machine:** Includes a full **Undo** function. Made a mistake? Revert everything with one command.
*   🧠 **Intelligent:** Detects duplicates and auto-renames them (`file_1.txt`) instead of overwriting data.
*   🔄 **Smart Dedup:** Detects identical files by content (SHA256 hash) – no more duplicate copies.
*   ⚡ **Zero Config:** No external dependencies. No config files. Just install and run.

## 🚀 Quick Start

### Installation

This tool uses the Python Standard Library only. No heavy dependencies.

```bash
# Clone & Install
git clone https://github.com/your-username/folder-extractor.git
cd folder-extractor
pip install .
```

### Usage

```bash
# Run interactive mode
folder-extractor

# Or automate specific tasks
folder-extractor --sort-by-type --depth 2
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
*Creates folders like `PDF/`, `IMAGES/`, `ARCHIVE/` and sorts files automatically.*

### 3. Targeted Extraction
Need only the PDFs from a deep project archive?
```bash
folder-extractor --type pdf --depth 3
```
*Extracts only `.pdf` files, max 3 levels deep. Everything else stays untouched.*

### 4. Clean up Link Collections
Collecting YouTube links from various `.url` or `.webloc` files?
```bash
folder-extractor --type url,webloc --domain youtube.com
```

### 5. Eliminate Duplicates
You have the same photos in 10 different folders?
```bash
folder-extractor --deduplicate --global-dedup
```
*Detects identical files by content and keeps only one copy.*

### 6. "Oops, I didn't mean to do that!"
Did you extract files that should have stayed where they were?
```bash
folder-extractor --undo
```
*Restores the previous state completely.*

---

## 🛠️ Command Reference

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
| `--version`, `-v` | Shows the installed version. |

---

## 🔒 Safety Concept

To prevent data loss, Folder Extractor enforces strict rules:

1.  **Whitelist Paths:** Operations are denied unless executed within `~/Desktop`, `~/Downloads`, or `~/Documents`.
2.  **System Protection:** Automatically ignores system files like `.DS_Store`, `Thumbs.db`, and `.git` directories.
3.  **No Overwriting:** If `file.txt` exists, the new file becomes `file_1.txt`. Data is **never** overwritten.
4.  **Confirmation:** You must explicitly confirm before any destructive action starts (except in Undo mode).

---

## 💻 Development

Contributions are welcome! The project is modular and extensively tested.

```bash
# Setup development environment
pip install -e ".[test]"

# Run tests
pytest tests/
```

For detailed architectural information, please check [ARCHITECTURE.md](ARCHITECTURE.md).

## 📄 License

MIT License - Copyright (c) 2024 Philipp Briese

---
*Made with ❤️ and Python.*