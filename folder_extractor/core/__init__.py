"""
Core business logic for Folder Extractor.
"""

from .archives import (
    IArchiveHandler,
    TarHandler,
    ZipHandler,
    get_archive_handler,
)
from .security import (
    APIKeyError,
    load_api_key,
    load_google_api_key,
)

# AI modules require google-generativeai (Python 3.9+ only)
# Make imports optional to maintain Python 3.8 compatibility for core features
try:
    from .ai_async import (
        AIClientError,
        AsyncGeminiClient,
        IAIClient,
    )
    from .ai_resilience import (
        ai_retry,
        create_ai_retry_decorator,
    )
except ImportError:
    # google-generativeai not installed (e.g., Python 3.8)
    # AI features will not be available
    pass
