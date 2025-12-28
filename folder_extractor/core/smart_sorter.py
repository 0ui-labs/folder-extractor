"""
Smart Sorter module for AI-powered document categorization.

Orchestrates the interaction between the AI client and prompt generation
to analyze and categorize files automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from folder_extractor.config.constants import DEFAULT_CATEGORIES
from folder_extractor.core.ai_async import IAIClient
from folder_extractor.core.ai_prompts import get_system_prompt

if TYPE_CHECKING:
    from folder_extractor.config.settings import Settings


class SmartSorter:
    """
    AI-powered document sorter using Gemini for categorization.

    Combines file analysis with configurable categories to produce
    structured sorting decisions (category, sender, year).

    Attributes:
        client: AI client for file analysis
        settings: Settings instance for category configuration

    Example:
        >>> client = AsyncGeminiClient()
        >>> sorter = SmartSorter(client)
        >>> result = await sorter.process_file(Path("invoice.pdf"), "application/pdf")
        >>> print(result["category"])
        "Finanzen"
    """

    def __init__(
        self,
        client: IAIClient,
        settings: Optional[Settings] = None,
    ) -> None:
        """
        Initialize SmartSorter with AI client and optional settings.

        Args:
            client: AI client implementing IAIClient (e.g., AsyncGeminiClient)
            settings: Settings instance for category configuration.
                Falls back to global settings if not provided.
        """
        self._client = client
        if settings is None:
            from folder_extractor.config.settings import settings as global_settings

            self._settings = global_settings
        else:
            self._settings = settings

    def _get_all_categories(self) -> list[str]:
        """
        Get combined list of user-defined and default categories.

        User categories take precedence over default categories.
        Duplicates are removed while preserving order.

        Returns:
            List of category names with user categories first.
        """
        custom: list[str] = self._settings.get("custom_categories", [])
        return custom + [cat for cat in DEFAULT_CATEGORIES if cat not in custom]

    async def process_file(
        self,
        filepath: Path,
        mime_type: str,
    ) -> dict[str, Any]:
        """
        Analyze and categorize a file using AI.

        Loads available categories, generates the analysis prompt,
        and sends the file to the AI client for processing.

        Args:
            filepath: Path to the file to analyze
            mime_type: MIME type of the file (e.g., "image/jpeg", "application/pdf")

        Returns:
            Dictionary containing categorization results:
                - category: The assigned category name
                - sender: Extracted sender/company name (or None)
                - year: Extracted year from document (or None)

        Raises:
            AIClientError: If file analysis fails (propagated from client)

        Example:
            >>> result = await sorter.process_file(
            ...     Path("/path/to/invoice.pdf"),
            ...     "application/pdf"
            ... )
            >>> result
            {"category": "Finanzen", "sender": "Telekom", "year": "2024"}
        """
        categories = self._get_all_categories()
        prompt = get_system_prompt(categories)

        # Call AI client and return result directly
        # AIClientError is not caught - propagated to caller
        return await self._client.analyze_file(
            filepath=filepath,
            mime_type=mime_type,
            prompt=prompt,
        )
