"""
Smart Sorter module for AI-powered document categorization.

Orchestrates the interaction between the AI client and prompt generation
to analyze and categorize files automatically. Integrates with KnowledgeGraph
for document metadata storage and entity tracking.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from folder_extractor.config.constants import DEFAULT_CATEGORIES
from folder_extractor.config.settings import get_all_categories
from folder_extractor.core.ai_async import IAIClient
from folder_extractor.core.ai_prompts import get_system_prompt
from folder_extractor.core.file_operations import FileOperations

if TYPE_CHECKING:
    from folder_extractor.config.settings import Settings

logger = logging.getLogger(__name__)


class SmartSorter:
    """
    AI-powered document sorter using Gemini for categorization.

    Combines file analysis with configurable categories to produce
    structured sorting decisions (category, sender, year, entities).
    Automatically ingests document metadata into the KnowledgeGraph.

    Attributes:
        client: AI client for file analysis
        settings: Settings instance for category configuration

    Example:
        >>> client = AsyncGeminiClient()
        >>> sorter = SmartSorter(client)
        >>> result = await sorter.process_file(Path("invoice.pdf"), "application/pdf")
        >>> print(result["category"])
        "Finanzen"
        >>> print(result["entities"])
        [{"name": "Telekom", "type": "Organization"}]
    """

    def __init__(
        self,
        client: IAIClient,
        settings: Settings,
    ) -> None:
        """
        Initialize SmartSorter with AI client and settings.

        Args:
            client: AI client implementing IAIClient (e.g., AsyncGeminiClient)
            settings: Settings instance for category configuration (required)
        """
        self._client = client
        self._file_ops = FileOperations()
        self._settings = settings

    async def process_file(
        self,
        filepath: Path,
        mime_type: str,
    ) -> dict[str, Any]:
        """
        Analyze and categorize a file using AI.

        Loads available categories, generates the analysis prompt,
        sends the file to the AI client for processing, and ingests
        the results into the KnowledgeGraph.

        Args:
            filepath: Path to the file to analyze
            mime_type: MIME type of the file (e.g., "image/jpeg", "application/pdf")

        Returns:
            Dictionary containing categorization results:
                - category: The assigned category name
                - sender: Extracted sender/company name (or None)
                - year: Extracted year from document (or None)
                - entities: List of extracted entities (or empty list)
                    Each entity is a dict with 'name' and 'type' keys

        Raises:
            AIClientError: If file analysis fails (propagated from client)

        Note:
            KnowledgeGraph ingestion errors are logged but not propagated,
            ensuring the main workflow continues even if graph storage fails.

        Example:
            >>> result = await sorter.process_file(
            ...     Path("/path/to/invoice.pdf"),
            ...     "application/pdf"
            ... )
            >>> result
            {"category": "Finanzen", "sender": "Telekom", "year": "2024",
             "entities": [{"name": "Telekom", "type": "Organization"}]}
        """
        categories = get_all_categories(self._settings)
        prompt = get_system_prompt(categories)

        # Call AI client - AIClientError is not caught, propagated to caller
        result = await self._client.analyze_file(
            filepath=filepath,
            mime_type=mime_type,
            prompt=prompt,
        )

        # KnowledgeGraph Integration - errors are logged but not propagated
        self._ingest_to_knowledge_graph(filepath, result)

        return result

    def _ingest_to_knowledge_graph(
        self,
        filepath: Path,
        result: dict[str, Any],
    ) -> None:
        """
        Ingest document metadata into KnowledgeGraph.

        This method is fail-safe: any errors are logged but not propagated,
        ensuring the main file processing workflow continues.

        Args:
            filepath: Path to the analyzed file
            result: AI analysis result containing category, sender, year, entities
        """
        try:
            # Lazy import inside try to handle missing kuzu dependency gracefully
            from folder_extractor.core.memory.graph import get_knowledge_graph

            # Calculate file hash
            file_hash = self._file_ops.calculate_file_hash(filepath)

            # Prepare file_info dictionary for ingestion
            file_info = {
                "path": str(filepath.resolve()),  # Absolute path
                "hash": file_hash,
                "summary": result.get("category", "Sonstiges"),  # Category as summary
                "timestamp": int(time.time()),
                "category": result.get("category"),
                "entities": result.get("entities", []),  # Entities from AI response
            }

            # Ingest into Knowledge Graph
            kg = get_knowledge_graph()
            kg.ingest(file_info)

            logger.info(f"Knowledge graph updated for: {filepath.name}")

        except ModuleNotFoundError:
            # kuzu or memory module not available - skip ingestion silently
            logger.warning(
                f"Knowledge graph unavailable (missing dependency), "
                f"skipping ingestion for: {filepath.name}"
            )
        except Exception as e:
            # All other errors (including KnowledgeGraphError) - log but don't propagate
            logger.warning(f"Failed to update knowledge graph for {filepath.name}: {e}")
