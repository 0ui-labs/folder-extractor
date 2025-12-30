"""
Memory module for knowledge graph operations.

This module provides graph-based storage for document metadata,
entities, and their relationships using KùzuDB.
"""

from folder_extractor.core.memory.graph import (
    IKnowledgeGraph,
    KnowledgeGraph,
    KnowledgeGraphError,
    get_knowledge_graph,
    reset_knowledge_graph,
)

__all__ = [
    "IKnowledgeGraph",
    "KnowledgeGraph",
    "KnowledgeGraphError",
    "get_knowledge_graph",
    "reset_knowledge_graph",
]
