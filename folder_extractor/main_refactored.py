#!/usr/bin/env python3
"""
Folder Extractor - Refactored Version

This is a transitional file that imports from the new modular structure
while maintaining backward compatibility.
"""

import os
import sys
import json
import shutil
import argparse
import threading
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import platform

# Import from new structure
from folder_extractor.config.constants import (
    VERSION, AUTHOR, SAFE_FOLDER_NAMES, HIDDEN_FILE_PREFIX,
    GIT_DIRECTORY, HISTORY_FILE_NAME, FILE_TYPE_FOLDERS,
    NO_EXTENSION_FOLDER, MESSAGES, HELP_TEXT,
    DEFAULT_MAX_DEPTH, PROGRESS_BAR_WIDTH
)

from folder_extractor.config.settings import settings, configure_from_args

from folder_extractor.utils.parsers import (
    parse_file_types as parse_dateitypen,
    parse_domains
)

from folder_extractor.utils.file_validators import (
    is_temp_or_system_file as ist_temp_oder_system_datei,
    is_git_path as ist_git_pfad,
    should_include_file,
    validate_file_extension
)

from folder_extractor.utils.path_validators import (
    is_safe_path as ist_sicherer_pfad,
    normalize_path
)

from folder_extractor.utils.terminal import (
    save_terminal_settings,
    restore_terminal_settings,
    clear_line,
    format_progress_bar,
    Color
)

# Global abort signal (will be moved to proper state management)
abort_signal = threading.Event()

# Re-export all functions that were in the original main.py
# This ensures backward compatibility during migration

# For now, we'll keep the original implementations here
# In the next phase, these will be moved to their respective modules

# Placeholder for remaining functions that haven't been migrated yet
# These will be extracted in subsequent phases