"""
Constants and configuration values for Folder Extractor.

This module centralizes all constants, making them easy to modify
and test. All values that were previously hardcoded are now here.
"""

# Version Information
VERSION = "1.3.3"
AUTHOR = "Philipp Briese"


# Safe Paths Configuration
SAFE_FOLDER_NAMES = ["Desktop", "Downloads", "Documents"]


# File System Constants
HIDDEN_FILE_PREFIX = "."
GIT_DIRECTORY = ".git"
HISTORY_FILE_NAME = ".folder_extractor_history.json"


# Temporary and System Files
TEMP_EXTENSIONS = {
    ".tmp",
    ".temp",
    ".part",
    ".partial",
    ".crdownload",
    ".download",
    ".downloading",
    ".lock",
    ".lck",
}

SYSTEM_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".localized",
    "._*",
    "~$*",
    ".~*",
    HISTORY_FILE_NAME,  # Protect history file from being moved
}

EDITOR_TEMP_FILES = {
    ".swp",
    ".swo",
    ".swn",
    ".swm",  # Vim
    ".#*",
    "#*#",  # Emacs
    "~*",  # General backup
    ".bak",
    ".backup",
    ".old",
}

GIT_TEMP_FILES = {
    "COMMIT_EDITMSG",
    "HEAD",
    "FETCH_HEAD",
    "ORIG_HEAD",
    "MERGE_HEAD",
    "REBASE_HEAD",
}


# File Type Mappings for Sort-by-Type
FILE_TYPE_FOLDERS = {
    # Documents
    ".pdf": "PDF",
    ".doc": "DOC",
    ".docx": "DOC",
    ".odt": "ODT",
    ".rtf": "RTF",
    ".tex": "TEX",
    # Spreadsheets
    ".xls": "EXCEL",
    ".xlsx": "EXCEL",
    ".ods": "ODS",
    ".csv": "CSV",
    # Presentations
    ".ppt": "POWERPOINT",
    ".pptx": "POWERPOINT",
    ".odp": "ODP",
    # Images
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".gif": "GIF",
    ".bmp": "BMP",
    ".svg": "SVG",
    ".ico": "ICO",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".webp": "WEBP",
    ".heic": "HEIC",
    ".heif": "HEIC",
    # Videos
    ".mp4": "VIDEO",
    ".avi": "VIDEO",
    ".mkv": "VIDEO",
    ".mov": "VIDEO",
    ".wmv": "VIDEO",
    ".flv": "VIDEO",
    ".webm": "VIDEO",
    ".m4v": "VIDEO",
    ".mpg": "VIDEO",
    ".mpeg": "VIDEO",
    # Audio
    ".mp3": "AUDIO",
    ".wav": "AUDIO",
    ".flac": "AUDIO",
    ".aac": "AUDIO",
    ".ogg": "AUDIO",
    ".wma": "AUDIO",
    ".m4a": "AUDIO",
    ".opus": "AUDIO",
    # Archives
    ".zip": "ZIP",
    ".rar": "RAR",
    ".7z": "7ZIP",
    ".tar": "TAR",
    ".gz": "GZ",
    ".bz2": "BZ2",
    ".xz": "XZ",
    # Code
    ".py": "PYTHON",
    ".js": "JAVASCRIPT",
    ".ts": "TYPESCRIPT",
    ".java": "JAVA",
    ".cpp": "CPP",
    ".c": "C",
    ".h": "C",
    ".cs": "CSHARP",
    ".php": "PHP",
    ".rb": "RUBY",
    ".go": "GO",
    ".rs": "RUST",
    ".swift": "SWIFT",
    ".kt": "KOTLIN",
    ".r": "R",
    ".m": "MATLAB",
    # Web
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    # Data
    ".json": "JSON",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "CONFIG",
    ".conf": "CONFIG",
    # Text
    ".txt": "TEXT",
    ".md": "MARKDOWN",
    ".rst": "RST",
    ".log": "LOG",
    # Database
    ".sql": "SQL",
    ".db": "DATABASE",
    ".sqlite": "SQLITE",
    # Fonts
    ".ttf": "FONT",
    ".otf": "FONT",
    ".woff": "FONT",
    ".woff2": "FONT",
    # Other
    ".iso": "ISO",
    ".dmg": "DMG",
    ".exe": "EXE",
    ".app": "APP",
    ".deb": "DEB",
    ".rpm": "RPM",
}


# Default folder name for files without extension
NO_EXTENSION_FOLDER = "OHNE_ERWEITERUNG"


# Archive extensions that can be extracted
ARCHIVE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".tar.gz",
    ".tgz",
    ".bz2",
    ".tar.bz2",
    ".xz",
    ".tar.xz",
}


# Progress Bar Configuration
PROGRESS_BAR_WIDTH = 50


# User Interface Messages (German)
MESSAGES = {
    "WELCOME": """
Folder Extractor v{version}
Von {author}

Dieses Tool extrahiert alle Dateien aus Unterordnern in das aktuelle Verzeichnis.
""",
    "SECURITY_ERROR": """
⚠  SICHERHEITSWARNUNG: Dieses Tool darf nur in folgenden Ordnern ausgeführt werden:
   - Desktop
   - Downloads  
   - Documents
   
Aktueller Pfad: {path}

Bitte navigieren Sie zu einem der erlaubten Ordner.
""",
    "NO_FILES_FOUND": "Keine Dateien in Unterordnern gefunden.",
    "FILES_FOUND": "\n{count} Dateien in Unterordnern gefunden.",
    "CONFIRM_MOVE": "\nMöchten Sie diese Dateien hierher verschieben? (j/n): ",
    "OPERATION_CANCELLED": "\nOperation abgebrochen.",
    "MOVING_FILES": "\nVerschiebe Dateien...",
    "DRY_RUN_PREFIX": "[TEST] ",
    "MOVE_SUCCESS": "✓ {file}",
    "MOVE_ERROR": "✗ Fehler bei {file}: {error}",
    "DUPLICATE_RENAMED": "⚠  {old} → {new} (umbenannt)",
    "CONTENT_DUPLICATES_SKIPPED": "Identische Inhalte übersprungen (nicht dupliziert)",
    "OPERATION_ABORTED": "\n\n⚠  Operation wurde abgebrochen!",
    "MOVE_SUMMARY": """

==================================================
Zusammenfassung:
✓ {moved} Dateien verschoben
⚠  {duplicates} Dateien umbenannt (Duplikate)
✗ {errors} Fehler
==================================================
""",
    "EMPTY_FOLDERS_REMOVED": "\n✓ {count} leere Ordner entfernt.",
    "FOLDERS_NOT_REMOVED": "⚠  {count} Ordner nicht gelöscht:",
    "FOLDER_SKIP_REASON": "   • {name}: {reason}",
    "UNDO_AVAILABLE": "\nRückgängig machen mit: folder-extractor --undo",
    "UNDO_NO_HISTORY": "Keine Verlaufsdatei gefunden. Nichts zum Rückgängigmachen.",
    "UNDO_SUCCESS": "✓ {file} wiederhergestellt",
    "UNDO_ERROR": "✗ Fehler beim Wiederherstellen von {file}: {error}",
    "UNDO_SUMMARY": "\n✓ {count} Dateien erfolgreich wiederhergestellt.",
    "SORT_BY_TYPE_CREATING": "\nErstelle Ordnerstruktur nach Dateityp...",
    "SORT_BY_TYPE_CREATED": "✓ Ordner '{folder}' erstellt",
    "ABORT_HINT": "\nDrücke Ctrl+C zum Abbrechen...",
    # Global deduplication messages
    "INDEXING_TARGET": "Indiziere Zielordner...",
    "DEDUP_NAME_DUPLICATES": "Namens-Duplikate",
    "DEDUP_CONTENT_DUPLICATES": "Lokale Inhalts-Duplikate",
    "DEDUP_GLOBAL_DUPLICATES": "Globale Inhalts-Duplikate",
    # Archive extraction messages
    "EXTRACTING_ARCHIVE": "Entpacke {archive}...",
    "ARCHIVE_EXTRACTED": "✓ {archive} entpackt ({count} Dateien)",
    "ARCHIVE_EXTRACT_ERROR": "✗ Fehler beim Entpacken von {archive}: {error}",
    "ARCHIVE_DELETED": "✓ Archiv {archive} gelöscht",
    "ARCHIVE_DELETE_ERROR": "✗ Fehler beim Löschen von {archive}: {error}",
    "ARCHIVE_SECURITY_ERROR": "⚠ SICHERHEIT: {archive} hat unsichere Pfade",
}


# Help Text
HELP_TEXT = """
Folder Extractor - Dateien aus Unterordnern extrahieren

Verwendung:
    folder-extractor [OPTIONEN]

Optionen:
    -h, --help              Diese Hilfe anzeigen
    -v, --version           Version anzeigen
    -d, --depth TIEFE       Maximale Ordnertiefe (0 = unbegrenzt, Standard: 0)
    -t, --type TYPEN        Nur bestimmte Dateitypen (z.B. pdf,jpg,mp3)
    -n, --dry-run           Testlauf - zeigt was passieren würde
    -s, --sort-by-type      Dateien nach Typ in Unterordner sortieren
    -u, --undo              Letzte Operation rückgängig machen
    --include-hidden        Versteckte Dateien einbeziehen
    --deduplicate           Identische Dateien (gleicher Inhalt) nicht duplizieren
    --global-dedup          Globale Deduplizierung über gesamten Zielordner
                            ⚠ WARNUNG: Kann bei großen Ordnern langsam sein!
    --domain DOMAINS        Nur Weblinks von bestimmten Domains (z.B. youtube.com)
    --extract-archives      Archive (ZIP, TAR, GZ) entpacken und Inhalt extrahieren
    --delete-archives       Original-Archive nach erfolgreichem Entpacken löschen
                            (nur wirksam mit --extract-archives)

Beispiele:
    # Alle Dateien aus Unterordnern extrahieren
    folder-extractor
    
    # Nur PDFs und Bilder extrahieren
    folder-extractor --type pdf,jpg,png
    
    # Dateien nach Typ sortiert extrahieren
    folder-extractor --sort-by-type
    
    # Nur Dateien aus direkten Unterordnern (Tiefe 1)
    folder-extractor --depth 1
    
    # Testlauf ohne Dateien zu verschieben
    folder-extractor --dry-run
    
    # Nur YouTube-Links extrahieren
    folder-extractor --type url,webloc --domain youtube.com

    # Duplikate vermeiden (nur eindeutige Inhalte behalten)
    folder-extractor --deduplicate
    # Zeigt in der Zusammenfassung: "Identisch: X" für übersprungene Dateien

    # Globale Deduplizierung (prüft ALLE Dateien im Zielordner)
    folder-extractor --global-dedup
    # Findet Duplikate auch wenn Dateinamen unterschiedlich sind

    # Archive entpacken und Inhalt extrahieren
    folder-extractor --extract-archives
    # Archive nach dem Entpacken löschen
    folder-extractor --extract-archives --delete-archives

    # Letzte Operation rückgängig machen
    folder-extractor --undo

Sicherheit:
    Das Tool funktioniert nur in den Ordnern Desktop, Downloads und Documents.
    
Tastenkürzel:
    Ctrl+C - Operation abbrechen (während Dateien verschoben werden)
"""


# Error Messages
ERROR_MESSAGES = {
    "PERMISSION_DENIED": "Zugriff verweigert",
    "FILE_NOT_FOUND": "Datei nicht gefunden",
    "DISK_FULL": "Nicht genügend Speicherplatz",
    "INVALID_PATH": "Ungültiger Pfad",
    "UNKNOWN_ERROR": "Unbekannter Fehler",
}


# Limits and Defaults
MAX_PATH_LENGTH = 255  # Maximum file path length
DEFAULT_MAX_DEPTH = 0  # 0 means unlimited
PROGRESS_UPDATE_INTERVAL = 0.1  # seconds between progress updates


# Performance Tuning
BATCH_SIZE = 100  # Number of files to process in one batch
CACHE_SIZE = 1000  # Number of paths to cache


# File Preprocessing Configuration (for AI API uploads)
PREPROCESSOR_MAX_FILE_SIZE_MB = 20  # Gemini API limit
PREPROCESSOR_MAX_IMAGE_DIMENSION = 2048  # Max image edge length
PREPROCESSOR_JPG_QUALITY = 85  # JPG compression quality
PREPROCESSOR_MAX_PDF_PAGES = 5  # Max PDF pages to extract
# Exotic image formats to convert to JPG
PREPROCESSOR_EXOTIC_IMAGE_FORMATS = {".tiff", ".tif", ".bmp", ".webp"}
