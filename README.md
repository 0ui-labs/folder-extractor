# Folder Extractor

An intelligent tool for extracting and organizing files from nested folder structures. From simple CLI operations to AI-powered document management.

**Version 2.0.0** | [CHANGELOG](CHANGELOG.md) | [Guide](docs/ANLEITUNG.md) | [Architecture](docs/ARCHITECTURE.md)

## ✨ Highlights

- 🤖 **AI-Powered Smart Sorting**: Automatic document categorization with Google Gemini
- 📦 **Archive Extraction**: Secure extraction of ZIP/TAR with Zip Slip Protection
- 👁️ **Watch Mode**: Automatic processing when new files arrive
- 🧠 **Knowledge Graph**: Natural language queries of your documents
- 🌐 **REST API**: Integration with native macOS/iOS apps
- 🔒 **Security First**: Path validation, Zip Slip protection, secure operations

## 🚀 Features

### Core Features (Python 3.8+)
- 🔒 **Security Validation**: Only runs in Desktop, Downloads, or Documents folders
- 📁 **Intelligent Duplicate Handling**: Content-based deduplication with SHA256
- 🎯 **Flexible Depth Control**: Determine how deep to search in folder structure
- 🗂️ **Sort by Type**: Automatically organize files into type folders (PDF/, JPEG/, etc.)
- 📎 **File Type Filter**: Extract only specific file types (pdf, jpg, mp3, etc.)
- 🌐 **Domain Filter**: Filter web links by specific domains
- 📦 **Archive Extraction**: Safely extract ZIP, TAR, TAR.GZ, TGZ
- 🔄 **Intelligent Deduplication**: Detects identical files based on content
- 🌍 **Global Deduplication**: Finds duplicates in entire target folder
- 👻 **Hidden Files**: Optionally include hidden files
- 🧹 **Automatic Cleanup**: Removes empty folders after moving
- ↩️ **Undo Function**: Reverses the last operation
- 🔍 **Dry-Run Mode**: Shows what would happen without doing it
- 📈 **Progress Display**: Real-time progress with Rich terminal output

### Advanced Features (Python 3.9+)
- 🤖 **AI-Powered Smart Sorting**: Gemini-based document categorization
  - Automatic detection: Category, sender, year, entities
  - Template-based path generation
  - Self-healing mechanism with error correction
- 👁️ **Watch Mode**: Automatic folder monitoring
  - File stability monitoring (waits until downloads complete)
  - Smart debouncing for efficient processing
  - Integration with AI categorization
- 🧠 **Knowledge Graph**: KùzuDB-based metadata storage
  - Natural Language Queries: `folder-extractor --ask "Which invoices from Apple?"`
  - Entity relationships and document context
  - Cypher query translation
- 🌐 **REST API & WebSocket**: FastAPI-based for native apps
  - 8 REST endpoints for file processing and zones
  - WebSocket for real-time updates
  - Dropzone management with templates

## 📦 Installation

### Basic Installation (CLI Mode - Python 3.8+)

```bash
# Standard installation
pip install .

# For development (editable)
pip install -e .

# With test dependencies
pip install -e ".[test]"
```

### Advanced Features (Python 3.9+)

```bash
# AI/API features
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv google-generativeai kuzu watchdog

# Or only specific features
pip install google-generativeai kuzu  # AI + Knowledge Graph
pip install watchdog                   # Watch Mode
pip install fastapi uvicorn[standard]  # REST API
```

After installation:
- `folder-extractor` - CLI tool (available system-wide)
- `folder-extractor-api` - API server (only with API dependencies)

## 🎯 Quick Start

### Basic Usage

```bash
# Extract all files from subdirectories
cd ~/Downloads/MyFolder
folder-extractor

# Test run (only shows what would happen)
folder-extractor --dry-run

# Sort by file type
folder-extractor --sort-by-type

# Only specific file types
folder-extractor --type pdf,jpg,png

# Avoid duplicates
folder-extractor --deduplicate --global-dedup
```

### Archive Extraction

```bash
# Extract archives
folder-extractor --extract-archives

# Extract archives and delete originals
folder-extractor --extract-archives --delete-archives

# Extract archives and sort by type
folder-extractor --extract-archives --sort-by-type
```

### Watch Mode (Python 3.9+)

```bash
# Automatically monitor folder
folder-extractor --watch --sort-by-type

# With archive extraction
folder-extractor --watch --extract-archives --delete-archives

# Stop with Ctrl+C
```

### Knowledge Graph Queries (Python 3.9+)

```bash
# Natural language queries
folder-extractor --ask "Which insurance documents do I have?"
folder-extractor --ask "Show me invoices from Apple in 2024"
folder-extractor --ask "Which contracts are expiring?"
```

## 📚 Usage

### File Type Filter

Extract only specific file types:

```bash
# Only PDFs
folder-extractor --type pdf

# Multiple types
folder-extractor --type pdf,doc,docx,txt

# Only images from 2 levels
folder-extractor --type jpg,jpeg,png,heic --depth 2

# Only videos
folder-extractor --type mp4,avi,mkv,mov
```

**Supported types**: pdf, doc, docx, txt, jpg, jpeg, png, gif, mp4, mp3, wav, json, xml, csv, py, js, java, cpp, html, css, url, webloc, and many more.

### Domain Filter for Web Links

Filter browser bookmarks by domain:

```bash
# Only YouTube links
folder-extractor --type url,webloc --domain youtube.com

# Multiple domains
folder-extractor --type url --domain github.com,stackoverflow.com,reddit.com

# With subdomains (youtube.com also matches m.youtube.com)
folder-extractor --type url,webloc --domain youtube.com --depth 3
```

### Sort by Type

Automatically organize files into type-specific folders:

```bash
# Automatically sort
folder-extractor --sort-by-type

# Combined with other options
folder-extractor --sort-by-type --deduplicate
folder-extractor --sort-by-type --extract-archives
```

**Result:**
```
Downloads/
├── PDF/       (all .pdf files)
├── JPEG/      (all .jpg and .jpeg files)
├── PNG/       (all .png files)
├── VIDEO/     (all .mp4, .avi, .mkv files)
└── DOCX/      (all .docx files)
```

### Intelligent Deduplication

Avoid duplicates based on file content:

```bash
# Content-based deduplication
folder-extractor --deduplicate

# Global deduplication (checks entire target folder)
folder-extractor --global-dedup

# Combined with sorting
folder-extractor --sort-by-type --deduplicate --global-dedup
```

**What happens:**
- `--deduplicate`: Files with same name + same content are skipped
- `--global-dedup`: Finds duplicates even with different filenames
- Hash comparison: SHA256 with size-based pre-filtering for performance

### Hidden Files

Include hidden files (starting with `.`):

```bash
# All files including hidden
folder-extractor --include-hidden

# Hidden configuration files
folder-extractor --type json,yml,env --include-hidden
```

**Note:** System files like `.DS_Store` are still ignored.

### Undo Function

Reverse the last operation:

```bash
# Undo last operation
folder-extractor --undo
```

Each operation is saved in `~/.config/folder_extractor/history/` and can be fully restored.

## 🔐 Security

### Safe Folders

The tool **only** runs in these folders:
- `~/Desktop/*`
- `~/Downloads/*`
- `~/Documents/*`

This prevents accidental execution in system folders.

### Archive Security (Zip Slip Protection)

With `--extract-archives`:
- ✅ All extracted paths are validated
- ✅ Absolute paths in archives are rejected
- ✅ Path traversal attacks (`../../../etc/passwd`) are blocked
- ✅ Symlink resolution to prevent escapes

**Supported formats:** ZIP, TAR, TAR.GZ, TGZ

## 🌐 REST API Server (Python 3.9+)

### Installation

```bash
pip install fastapi uvicorn[standard] pydantic>=2.0.0 websockets python-dotenv
```

### Start Server

```bash
# Standard: localhost:23456
folder-extractor-api

# Custom port
folder-extractor-api --port 8000

# Development mode with auto-reload
folder-extractor-api --reload

# All options
folder-extractor-api --host 127.0.0.1 --port 23456 --log-level debug --reload
```

After starting, available at:
- **API Docs:** `http://localhost:23456/docs` (interactive)
- **Alternative Docs:** `http://localhost:23456/redoc`

### Available Endpoints

#### Health & Status
- `GET /health` - Check server status

#### File Processing
- `POST /api/v1/process` - Process single file

#### Dropzone Management
- `GET /api/v1/zones` - List all dropzones
- `POST /api/v1/zones` - Create new dropzone
- `DELETE /api/v1/zones/{zone_id}` - Delete dropzone

#### Watch Mode (API)
- `POST /api/v1/watcher/start` - Start watcher for zone
- `POST /api/v1/watcher/stop` - Stop watcher
- `GET /api/v1/watcher/status` - Status of all watchers

#### WebSocket
- `WS /ws/chat` - Bidirectional communication for real-time updates

### Example Request

```bash
# Health check
curl http://localhost:23456/health

# Process file
curl -X POST http://localhost:23456/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/Users/username/Desktop/document.pdf"}'

# Create dropzone
curl -X POST http://localhost:23456/api/v1/zones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Documents",
    "path": "/Users/username/Desktop/Dropzone",
    "enabled": true,
    "auto_sort": true,
    "categories": ["Finance", "Contracts"]
  }'
```

### WebSocket Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:23456/ws/chat');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Type:', message.type);
  console.log('Data:', message.data);
};

ws.send(JSON.stringify({
  type: 'query',
  data: { question: 'Which PDFs do I have?' }
}));
```

### Swift Integration (macOS/iOS)

```swift
import Foundation

// HTTP Request
let url = URL(string: "http://localhost:23456/api/v1/process")!
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")

let body: [String: Any] = ["filepath": "/Users/username/Desktop/document.pdf"]
request.httpBody = try? JSONSerialization.data(withJSONObject: body)

URLSession.shared.dataTask(with: request) { data, response, error in
    // Handle response
}.resume()

// WebSocket
let wsURL = URL(string: "ws://localhost:23456/ws/chat")!
let webSocket = URLSession.shared.webSocketTask(with: wsURL)
webSocket.resume()

webSocket.receive { result in
    switch result {
    case .success(let message):
        // Handle message
    case .failure(let error):
        print("Error: \(error)")
    }
}
```

### Configuration

Create `.env` file:

```bash
API_PORT=23456
API_HOST=127.0.0.1
API_LOG_LEVEL=info
GEMINI_API_KEY=your-api-key-here
```

### Security Notes

⚠️ **Important for Production:**
- Server runs by default only on `localhost` (127.0.0.1)
- For external connections: `API_HOST=0.0.0.0` (not recommended without auth)
- CORS is configured for `localhost`
- For production environments: Implement authentication

## 📖 Documentation

- **[ANLEITUNG.md](docs/ANLEITUNG.md)** - Comprehensive user guide in German
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture documentation and design patterns
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for Claude Code

## 💻 System Requirements

### Basic (CLI Mode)
- **Python**: 3.8 or higher
- **Operating Systems**: macOS, Linux, Windows
- **Runtime Dependencies**: `rich>=13.0.0`

### Advanced Features
- **Python**: 3.9 or higher (for AI/API features)
- **Optional Dependencies**:
  - `google-generativeai` - AI Smart Sorting
  - `kuzu` - Knowledge Graph
  - `watchdog` - Watch Mode
  - `fastapi`, `uvicorn`, `pydantic`, `websockets` - REST API

## 🔄 Example Workflows

### 1. Clean up Downloads

```bash
cd ~/Downloads
folder-extractor --dry-run --sort-by-type  # Test first
folder-extractor --sort-by-type --deduplicate  # Then execute
```

### 2. Consolidate Photo Collection

```bash
cd ~/Pictures/Vacation
folder-extractor --type jpg,jpeg,png,heic --deduplicate --global-dedup
```

### 3. Organize Backup Archives

```bash
cd ~/Documents/Backups
folder-extractor --extract-archives --sort-by-type
# Originals remain, OR:
folder-extractor --extract-archives --delete-archives --sort-by-type
```

### 4. Automatically Organize Downloads Folder

```bash
cd ~/Downloads
folder-extractor --watch --sort-by-type --extract-archives
# Runs continuously, Ctrl+C to stop
```

### 5. Organize Documents with AI (Python 3.9+)

```bash
# Configure API key
export GEMINI_API_KEY=your-key

# Automatic categorization
cd ~/Documents/Inbox
folder-extractor --watch --sort-by-type

# Query later
folder-extractor --ask "Which insurance documents do I have from 2024?"
```

## 🤝 Contributing

Contributions are welcome! See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details on codebase structure.

**Development:**
```bash
# Install with test dependencies
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

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Credits

- Developed by **Philipp Briese**
- AI Integration: Google Gemini 3 Flash Preview
- Graph Database: KùzuDB
- Terminal UI: Rich Library
- Web Framework: FastAPI

---

**Happy organizing!** 🗂️

For questions and issues: `folder-extractor --help` or [GitHub Issues](https://github.com/0ui-labs/folder-extractor/issues)
