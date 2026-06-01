"""hermes_memory — vector (ChromaDB) + graph (SQLite) memory layer.

Public API
----------
- MemoryManager : unified interface for all memory operations
- VectorMemory  : ChromaDB-backed semantic memory
- GraphMemory   : SQLite-backed directed property graph
- MemoryEntry, MemoryQueryResult, GraphNode, GraphEdge, GraphQueryResult
"""

from hermes_memory.graph import GraphMemory
from hermes_memory.manager import MemoryManager
from hermes_memory.schemas import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
    MemoryEntry,
    MemoryQueryResult,
)
from hermes_memory.vector import VectorMemory

__all__ = [
    "GraphEdge",
    "GraphMemory",
    "GraphNode",
    "GraphQueryResult",
    "MemoryEntry",
    "MemoryManager",
    "MemoryQueryResult",
    "VectorMemory",
]
