"""
Core business logic for Folder Extractor.
"""

from .archives import (
    IArchiveHandler,
    TarHandler,
    ZipHandler,
    get_archive_handler,
)
