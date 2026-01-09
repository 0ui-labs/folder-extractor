"""
Knowledge Graph module for document metadata and entity storage.

This module provides graph-based storage for document metadata,
entities, and their relationships using KùzuDB.

Usage:
    from folder_extractor.core.memory import KnowledgeGraph, get_knowledge_graph

    # Using context manager
    with KnowledgeGraph(db_path=Path("/tmp/test.db")) as kg:
        kg.ingest(file_info)

    # Using singleton
    kg = get_knowledge_graph()
    kg.ingest(file_info)
"""

from __future__ import annotations

import logging
import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import kuzu

from folder_extractor.core.file_operations import get_config_directory

logger = logging.getLogger(__name__)


def _get_cypher_translation_prompt(user_query: str, schema_info: str) -> str:
    """Generate prompt for Natural Language to Cypher translation.

    Creates a detailed prompt that instructs the AI model to convert
    a natural language query into a valid Cypher query for KùzuDB.

    Args:
        user_query: Natural language query from the user.
            Examples: "Zeig mir Rechnungen von Apple",
                     "Welche Versicherungsdokumente habe ich?"
        schema_info: Schema description of the knowledge graph.

    Returns:
        Complete prompt string for Gemini API.

    Example:
        >>> prompt = _get_cypher_translation_prompt(
        ...     "Finde Apple Dokumente",
        ...     "Graph Schema: ..."
        ... )
        >>> "Apple" in prompt
        True
    """
    return f'''Du bist ein Experte für Graph-Datenbanken und Cypher-Queries.

Deine Aufgabe: Übersetze die folgende natürlichsprachige Anfrage in eine
gültige Cypher-Query.

## Datenbank-Schema

{schema_info}

## Beispiel-Übersetzungen

1. "Zeig mir Rechnungen von Apple"
   → MATCH (d:Document)-[:MENTIONS]->(e:Entity {{name: 'Apple'}})
     WHERE d.summary CONTAINS 'Rechnung' OR d.summary CONTAINS 'Invoice'
     RETURN DISTINCT d.path

2. "Welche Versicherungsdokumente habe ich?"
   → MATCH (d:Document)-[:BELONGS_TO]->(c:Category)
     WHERE c.name = 'Versicherung' OR d.summary CONTAINS 'Versicherung'
     RETURN DISTINCT d.path

3. "Alle Dokumente von Telekom"
   → MATCH (d:Document)-[:MENTIONS]->(e:Entity {{name: 'Telekom'}})
     RETURN DISTINCT d.path

4. "Verträge aus 2024"
   → MATCH (d:Document)-[:BELONGS_TO]->(c:Category {{name: 'Verträge'}})
     WHERE d.timestamp >= 1704067200 AND d.timestamp < 1735689600
     RETURN DISTINCT d.path

## Wichtige Regeln

1. ALLE Queries MÜSSEN "d.path" zurückgeben (Dateipfade)
2. Verwende DISTINCT um Duplikate zu vermeiden
3. Nutze CONTAINS für Textssuche in summary
4. Entity-Namen sind case-sensitive
5. Generiere nur gültige Cypher-Syntax für KùzuDB

## Benutzeranfrage

"{user_query}"

## Antwortformat

Antworte NUR mit einem JSON-Objekt in diesem Format:
{{
    "cypher": "MATCH ... RETURN DISTINCT d.path",
    "explanation": "Kurze Erklärung der Query-Logik"
}}'''


class KnowledgeGraphError(Exception):
    """Raised when knowledge graph operations fail."""


# Forbidden keywords in AI-generated Cypher queries (write/DDL operations)
# CALL can execute stored procedures, REMOVE removes properties
_CYPHER_WRITE_KEYWORDS = frozenset(
    ["CREATE", "MERGE", "DELETE", "SET", "DROP", "ALTER", "CALL", "REMOVE"]
)


def _validate_cypher_readonly(cypher_query: str) -> None:
    """Validate that a Cypher query is read-only.

    Ensures AI-generated Cypher queries cannot perform write or DDL operations.
    This is a security guard to prevent the AI from modifying the database.

    Args:
        cypher_query: The Cypher query string to validate.

    Raises:
        KnowledgeGraphError: If the query contains write operations or
            doesn't start with MATCH/WITH.

    Example:
        >>> _validate_cypher_readonly("MATCH (d:Document) RETURN d.path")  # OK
        >>> _validate_cypher_readonly("CREATE (d:Document)")  # Raises error
    """
    # Normalize for checking
    query_upper = cypher_query.upper().strip()

    # Must start with MATCH or WITH (read-only query starters)
    if not query_upper.startswith("MATCH") and not query_upper.startswith("WITH"):
        raise KnowledgeGraphError(
            f"Cypher query must start with MATCH or WITH (read-only). "
            f"Got: {cypher_query[:50]}..."
        )

    # Check for semicolons (could be used for query chaining/injection)
    if ";" in cypher_query:
        raise KnowledgeGraphError(
            f"Cypher query contains forbidden semicolon. Got: {cypher_query[:50]}..."
        )

    # Tokenize and check for write keywords
    # Use simple word boundary check by splitting on non-alphanumeric chars
    tokens = set(re.findall(r"[A-Z]+", query_upper))

    forbidden_found = tokens & _CYPHER_WRITE_KEYWORDS
    if forbidden_found:
        raise KnowledgeGraphError(
            f"Cypher query contains forbidden write keywords: {forbidden_found}. "
            f"Only read-only queries are allowed. Got: {cypher_query[:50]}..."
        )


class IKnowledgeGraph(ABC):
    """Interface for knowledge graph operations.

    Defines the contract for graph-based document storage
    and retrieval operations.
    """

    @abstractmethod
    def initialize_schema(self) -> None:
        """Initialize the graph database schema.

        Creates node tables (Document, Entity, Category) and
        relationship tables (MENTIONS, BELONGS_TO) if they don't exist.
        """

    @abstractmethod
    def ingest(self, file_info: dict[str, Any]) -> None:
        """Ingest document metadata and entities into the graph.

        Args:
            file_info: Dictionary containing document metadata.
                Required keys: path, hash, timestamp
                Optional keys: summary, category, entities
        """

    @abstractmethod
    async def query_documents(self, filter_text: str) -> list[str]:
        """Query documents using natural language filter.

        Uses AI to translate natural language to Cypher queries
        and executes them against the knowledge graph.

        Args:
            filter_text: Natural language query string.

        Returns:
            List of matching document paths.

        Raises:
            KnowledgeGraphError: If query translation or execution fails.
        """

    @abstractmethod
    def close(self) -> None:
        """Close database connection and release resources."""


class KnowledgeGraph(IKnowledgeGraph):
    """KùzuDB-backed knowledge graph for document storage.

    Stores document metadata, entities, and their relationships
    in a property graph database. Supports MERGE operations for
    idempotent updates.

    Attributes:
        _db: KùzuDB Database instance
        _conn: KùzuDB Connection for executing queries

    Example:
        >>> with KnowledgeGraph(db_path=Path("/tmp/test.db")) as kg:
        ...     kg.ingest({
        ...         "path": "/docs/invoice.pdf",
        ...         "hash": "abc123",
        ...         "timestamp": 1234567890,
        ...         "category": "Invoices",
        ...         "entities": [{"name": "Acme Corp", "type": "ORGANIZATION"}]
        ...     })
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize KnowledgeGraph with database connection.

        Args:
            db_path: Path to the database directory. If not provided,
                uses the default config directory location.

        Raises:
            KnowledgeGraphError: If database initialization fails.
        """
        if db_path is None:
            db_path = get_config_directory() / "knowledge_graph.db"

        try:
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self._db: Optional[kuzu.Database] = kuzu.Database(str(db_path))
            self._conn: Optional[kuzu.Connection] = kuzu.Connection(self._db)
            self._db_path = db_path

            self.initialize_schema()

            logger.info(f"Knowledge graph initialized at: {db_path}")

        except Exception as e:
            raise KnowledgeGraphError(f"Failed to initialize database: {e}") from e

    def __enter__(self) -> KnowledgeGraph:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit context manager and close connection."""
        self.close()

    def _schema_exists(self) -> bool:
        """Check if schema tables already exist.

        Returns:
            True if Document table exists, False otherwise.
        """
        if self._conn is None:
            return False

        try:
            # Try to query the Document table - if it exists, schema is initialized
            result = self._conn.execute("MATCH (d:Document) RETURN count(d) LIMIT 1")
            result.get_next()
            return True
        except Exception:
            return False

    def initialize_schema(self) -> None:
        """Initialize graph database schema.

        Creates node tables for Document, Entity, and Category,
        plus relationship tables for MENTIONS and BELONGS_TO.

        This operation is idempotent - calling multiple times is safe.

        Raises:
            KnowledgeGraphError: If schema creation fails.
        """
        if self._conn is None:
            raise KnowledgeGraphError("Database connection not available")

        # Check if schema already exists
        if self._schema_exists():
            logger.debug("Schema already exists, skipping initialization")
            return

        try:
            # Create Node Tables
            self._conn.execute(
                """
                CREATE NODE TABLE Document(
                    path STRING,
                    hash STRING,
                    summary STRING,
                    timestamp INT64,
                    PRIMARY KEY (path)
                )
                """
            )

            self._conn.execute(
                """
                CREATE NODE TABLE Entity(
                    name STRING,
                    type STRING,
                    PRIMARY KEY (name)
                )
                """
            )

            self._conn.execute(
                """
                CREATE NODE TABLE Category(
                    name STRING,
                    PRIMARY KEY (name)
                )
                """
            )

            # Create Relationship Tables
            self._conn.execute(
                """
                CREATE REL TABLE MENTIONS(
                    FROM Document TO Entity
                )
                """
            )

            self._conn.execute(
                """
                CREATE REL TABLE BELONGS_TO(
                    FROM Document TO Category
                )
                """
            )

            logger.info("Knowledge graph schema initialized")

        except Exception as e:
            raise KnowledgeGraphError(f"Failed to create schema: {e}") from e

    def ingest(self, file_info: dict[str, Any]) -> None:
        """Ingest document metadata and entities into knowledge graph.

        Creates or updates Document node, Category node, Entity nodes,
        and their relationships (BELONGS_TO, MENTIONS).

        Args:
            file_info: Dictionary with keys:
                - path (str, required): Absolute file path
                - hash (str, required): SHA256 hash
                - timestamp (int, required): Unix timestamp
                - summary (str, optional): Document summary
                - category (str, optional): Category name
                - entities (List[Dict], optional): List of entities
                    Each entity: {"name": str, "type": str}

        Raises:
            KnowledgeGraphError: If ingestion fails or required fields missing.

        Example:
            >>> kg.ingest({
            ...     "path": "/path/to/file.pdf",
            ...     "hash": "abc123...",
            ...     "timestamp": 1234567890,
            ...     "category": "Finanzen",
            ...     "entities": [
            ...         {"name": "Apple Inc.", "type": "ORGANIZATION"}
            ...     ]
            ... })
        """
        if self._conn is None:
            raise KnowledgeGraphError("Database connection not available")

        # Validate required fields
        if "path" not in file_info:
            raise KnowledgeGraphError("file_info must contain 'path'")
        if "hash" not in file_info:
            raise KnowledgeGraphError("file_info must contain 'hash'")
        if "timestamp" not in file_info:
            raise KnowledgeGraphError("file_info must contain 'timestamp'")

        try:
            # 1. Create/Update Document Node
            self._conn.execute(
                """
                MERGE (d:Document {path: $path})
                SET d.hash = $hash,
                    d.summary = $summary,
                    d.timestamp = $timestamp
                """,
                {
                    "path": file_info["path"],
                    "hash": file_info["hash"],
                    "summary": file_info.get("summary", ""),
                    "timestamp": file_info["timestamp"],
                },
            )

            # 2. Category Node and BELONGS_TO relationship
            category = file_info.get("category")
            if category:
                # Create Category Node
                self._conn.execute(
                    "MERGE (c:Category {name: $name})",
                    {"name": category},
                )

                # Create BELONGS_TO relationship
                self._conn.execute(
                    """
                    MATCH (d:Document {path: $path})
                    MATCH (c:Category {name: $category})
                    MERGE (d)-[:BELONGS_TO]->(c)
                    """,
                    {"path": file_info["path"], "category": category},
                )

            # 3. Entity Nodes and MENTIONS relationships
            entities = file_info.get("entities", [])
            for entity in entities:
                if not isinstance(entity, dict):
                    logger.warning(f"Invalid entity format: {entity}")
                    continue

                entity_name = entity.get("name")
                entity_type = entity.get("type")

                if not entity_name or not entity_type:
                    logger.warning(f"Entity missing name or type: {entity}")
                    continue

                # Create Entity Node
                self._conn.execute(
                    """
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type
                    """,
                    {"name": entity_name, "type": entity_type},
                )

                # Create MENTIONS relationship
                self._conn.execute(
                    """
                    MATCH (d:Document {path: $path})
                    MATCH (e:Entity {name: $name})
                    MERGE (d)-[:MENTIONS]->(e)
                    """,
                    {"path": file_info["path"], "name": entity_name},
                )

            logger.info(f"Ingested document: {file_info['path']}")

        except KnowledgeGraphError:
            raise
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to ingest document: {e}") from e

    def _get_schema_info(self) -> str:
        """Generate schema description for Cypher translation prompts.

        Provides a human-readable description of the graph schema
        that helps the AI model generate valid Cypher queries.

        Returns:
            Formatted string describing nodes, relationships, and attributes.

        Example:
            >>> kg = KnowledgeGraph()
            >>> schema = kg._get_schema_info()
            >>> "Document" in schema
            True
        """
        return """Graph Schema:

Nodes:
- Document: Represents a file in the knowledge graph
  Attributes: path (string, PK), hash (string), summary (string), timestamp (int64)

- Entity: Represents a recognized entity (person, organization, etc.)
  Attributes: name (string, primary key), type (string)
  Types: ORGANIZATION, PERSON, PROJECT, LOCATION, PRODUCT, DATE

- Category: Represents a document category
  Attributes: name (string, primary key)
  Examples: Finanzen, Verträge, Medizin, Bildung, Rechnungen

Relationships:
- MENTIONS: Document -> Entity (document mentions an entity)
- BELONGS_TO: Document -> Category (document belongs to a category)

Important: All queries MUST return d.path (document file paths).
Use DISTINCT to avoid duplicate results when joining through relationships."""

    async def _call_gemini_for_text(self, prompt: str) -> dict[str, Any]:
        """Call Gemini API for pure text analysis without file upload.

        Uses the text-only generate_response API with JSON mode for
        efficient Natural Language to Cypher translation.

        Args:
            prompt: Text prompt to send to Gemini.

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            KnowledgeGraphError: If API call fails or response is invalid.
        """
        # Lazy import to avoid circular dependencies
        from folder_extractor.core.ai_async import AIClientError, AsyncGeminiClient

        try:
            client = AsyncGeminiClient()
            # Use direct text API with JSON response mode (no file upload needed)
            result = await client.generate_response(prompt, json_response=True)

            # Type guard: ensure result is dict (should always be true with json_response=True)
            if not isinstance(result, dict):
                raise KnowledgeGraphError(
                    f"Expected dict from JSON response, got {type(result).__name__}"
                )

            return result

        except AIClientError as e:
            raise KnowledgeGraphError(f"AI translation failed: {e}") from e
        except Exception as e:
            raise KnowledgeGraphError(f"Failed to call Gemini API: {e}") from e

    async def _translate_to_cypher(self, user_query: str) -> dict[str, str]:
        """Translate natural language query to Cypher using Gemini API.

        Generates a prompt with schema information and example queries,
        sends it to Gemini, and validates the response.

        Args:
            user_query: Natural language query from user.

        Returns:
            Dictionary with 'cypher' and 'explanation' keys.

        Raises:
            KnowledgeGraphError: If translation fails or result is invalid.

        Example:
            >>> result = await kg._translate_to_cypher("Zeig mir Apple Dokumente")
            >>> print(result["cypher"])
            MATCH (d:Document)-[:MENTIONS]->(e:Entity) RETURN DISTINCT d.path
        """
        try:
            # Generate prompt with schema info
            schema_info = self._get_schema_info()
            prompt = _get_cypher_translation_prompt(user_query, schema_info)

            # Call Gemini API
            logger.debug(f"Translating query: {user_query}")
            response = await self._call_gemini_for_text(prompt)

            # Validate response structure
            if "cypher" not in response:
                raise KnowledgeGraphError(
                    f"Invalid AI response: missing 'cypher' field. Response: {response}"
                )

            cypher_query = response["cypher"]

            # Validate that query returns d.path
            if "d.path" not in cypher_query:
                raise KnowledgeGraphError(
                    f"Generated Cypher query must return d.path. Got: {cypher_query}"
                )

            logger.debug(f"Generated Cypher: {cypher_query}")
            logger.info(f"Query translated successfully: {user_query[:50]}...")

            return {
                "cypher": cypher_query,
                "explanation": response.get("explanation", ""),
            }

        except KnowledgeGraphError:
            raise
        except Exception as e:
            raise KnowledgeGraphError(
                f"Failed to translate query '{user_query}': {e}"
            ) from e

    async def query_documents(self, filter_text: str) -> list[str]:
        """Query documents using natural language filter.

        Translates natural language to Cypher using Gemini API,
        executes the query on KùzuDB, and returns matching file paths.

        Args:
            filter_text: Natural language query string.
                Examples:
                - "Zeig mir Rechnungen von Apple"
                - "Welche Versicherungsdokumente habe ich?"
                - "Alle Dokumente von Telekom aus 2024"

        Returns:
            List of absolute file paths matching the query.
            Empty list if no documents match.

        Raises:
            KnowledgeGraphError: If query is invalid, translation fails,
                or Cypher execution fails.

        Example:
            >>> kg = get_knowledge_graph()
            >>> paths = await kg.query_documents("Zeig mir Apple Rechnungen")
            >>> print(paths)
            ['/path/to/invoice1.pdf', '/path/to/invoice2.pdf']
        """
        if self._conn is None:
            raise KnowledgeGraphError("Database connection not available")

        # Validate input
        filter_text = filter_text.strip()
        if not filter_text:
            raise KnowledgeGraphError("Query cannot be empty")

        if len(filter_text) > 500:
            raise KnowledgeGraphError(
                f"Query exceeds maximum length of 500 characters "
                f"(got {len(filter_text)})"
            )

        try:
            # Translate natural language to Cypher
            translation = await self._translate_to_cypher(filter_text)
            cypher_query = translation["cypher"]

            # Security guard: Ensure query is read-only
            _validate_cypher_readonly(cypher_query)

            logger.debug(f"Executing Cypher: {cypher_query}")

            # Execute query on KùzuDB
            try:
                result = self._conn.execute(cypher_query)
            except Exception as e:
                raise KnowledgeGraphError(
                    f"Cypher execution failed: {e}. Query: {cypher_query}"
                ) from e

            # Extract paths from results
            paths: list[str] = []
            while result.has_next():
                row = result.get_next()
                if row and row[0] is not None:
                    paths.append(row[0])

            # Deduplicate while preserving order
            seen: set[str] = set()
            unique_paths: list[str] = []
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    unique_paths.append(path)

            logger.info(f"Query found {len(unique_paths)} documents")

            return unique_paths

        except KnowledgeGraphError:
            raise
        except Exception as e:
            raise KnowledgeGraphError(
                f"Query failed: {e}. Filter: {filter_text}"
            ) from e

    def close(self) -> None:
        """Close database connection and release resources.

        Safe to call multiple times. After closing, the instance
        should not be used for further operations.
        """
        if self._conn is not None:
            # KùzuDB doesn't have explicit close, set to None for GC
            self._conn = None

        if self._db is not None:
            self._db = None

        logger.debug("Knowledge graph connection closed")


# Singleton pattern for global access (thread-safe)
_knowledge_graph_instance: Optional[KnowledgeGraph] = None
_knowledge_graph_lock = threading.Lock()


def get_knowledge_graph() -> KnowledgeGraph:
    """Get or create the global knowledge graph instance.

    Uses the default database path in the config directory.
    Thread-safe initialization using double-checked locking pattern.
    The returned instance is not thread-safe for concurrent writes.

    Returns:
        The global KnowledgeGraph instance.

    Example:
        >>> kg = get_knowledge_graph()
        >>> kg.ingest(file_info)
    """
    global _knowledge_graph_instance
    # Fast path: instance already exists
    if _knowledge_graph_instance is not None:
        return _knowledge_graph_instance
    # Slow path: acquire lock for initialization
    with _knowledge_graph_lock:
        # Double-check after acquiring lock
        if _knowledge_graph_instance is None:
            _knowledge_graph_instance = KnowledgeGraph()
    return _knowledge_graph_instance


def reset_knowledge_graph() -> None:
    """Reset the global knowledge graph instance.

    Closes the existing connection and clears the singleton.
    The next call to get_knowledge_graph() will create a new instance.
    Thread-safe.

    Use this for testing or when you need to reinitialize the database.

    Example:
        >>> reset_knowledge_graph()
        >>> kg = get_knowledge_graph()  # Fresh instance
    """
    global _knowledge_graph_instance
    with _knowledge_graph_lock:
        if _knowledge_graph_instance is not None:
            _knowledge_graph_instance.close()
            _knowledge_graph_instance = None
