"""MemoryManager — unified interface over vector + graph memory.

Provides a single facade for agent memory operations, routing to the
appropriate backend (vector or graph) based on the operation type.

Usage::

    mm = MemoryManager(base_dir="/tmp/hermes/memory")
    entry_id = mm.remember(agent_id="agent_1", text="important context")
    results = mm.recall(agent_id="agent_1", query="context", n=5)
    mm.link(source_id="node_a", target_id="node_b", relation="caused_by")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from hermes_memory.graph import GraphMemory
from hermes_memory.schemas import (
    GraphEdge,
    GraphNode,
    GraphQueryResult,
    MemoryEntry,
    MemoryQueryResult,
)
from hermes_memory.vector import VectorMemory

log = structlog.get_logger(__name__)


class MemoryManager:
    """Facade combining :class:`VectorMemory` and :class:`GraphMemory`.

    Parameters
    ----------
    base_dir:
        Root directory for all memory storage.  Sub-directories
        ``chroma/`` and ``graph.db`` are created automatically.
    embedding_function:
        Optional custom ChromaDB embedding function passed to
        :class:`VectorMemory`.
    """

    def __init__(
        self,
        base_dir: str | Path,
        embedding_function: Any = None,
    ) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._vector = VectorMemory(
            persist_dir=self._base / "chroma",
            embedding_function=embedding_function,
        )
        self._graph = GraphMemory(path=self._base / "graph.db")
        log.info("memory_manager.initialised", base_dir=str(self._base))

    # ------------------------------------------------------------------ #
    # Vector memory                                                        #
    # ------------------------------------------------------------------ #

    def remember(
        self,
        agent_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a piece of textual memory for *agent_id*.

        Parameters
        ----------
        agent_id:
            The agent that owns this memory.
        text:
            The content to remember.
        metadata:
            Optional metadata dict stored alongside the embedding.

        Returns
        -------
        str
            The unique ID of the stored memory entry.
        """
        entry = MemoryEntry(
            content=text,
            agent_id=agent_id,
            metadata=metadata or {},
        )
        entry_id = self._vector.add(entry)
        log.debug("memory_manager.remembered", agent_id=agent_id, entry_id=entry_id)
        return entry_id

    def recall(
        self,
        agent_id: str,
        query: str,
        n: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[MemoryQueryResult]:
        """Semantic search over *agent_id*'s memories.

        Parameters
        ----------
        agent_id:
            Owner of the memories to search.
        query:
            Natural-language query to embed and search against.
        n:
            Maximum number of results.
        where:
            Optional metadata filter passed to ChromaDB.

        Returns
        -------
        list[MemoryQueryResult]
            Ranked by relevance (highest first).
        """
        return self._vector.query(text=query, agent_id=agent_id, n_results=n, where=where)

    def forget(self, agent_id: str, entry_id: str) -> bool:
        """Delete a specific memory entry.

        Returns
        -------
        bool
            ``True`` if the entry was found and deleted.
        """
        return self._vector.delete(entry_id=entry_id, agent_id=agent_id)

    def memory_count(self, agent_id: str) -> int:
        """Return the number of stored memories for *agent_id*."""
        return self._vector.count(agent_id)

    # ------------------------------------------------------------------ #
    # Graph memory                                                         #
    # ------------------------------------------------------------------ #

    def add_concept(
        self,
        label: str,
        properties: dict[str, Any] | None = None,
        agent_id: str = "",
    ) -> GraphNode:
        """Add a concept node to the graph.

        Parameters
        ----------
        label:
            Node type label (e.g. ``"person"``, ``"tool"``, ``"concept"``).
        properties:
            Key-value metadata for the node.
        agent_id:
            Optional owning agent.

        Returns
        -------
        GraphNode
            The created node.
        """
        node = GraphNode(label=label, properties=properties or {}, agent_id=agent_id)
        return self._graph.add_node(node)

    def link(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> GraphEdge:
        """Create a directed edge between two nodes.

        Parameters
        ----------
        source_id:
            ID of the source node.
        target_id:
            ID of the target node.
        relation:
            Named relation type (e.g. ``"caused_by"``, ``"uses"``).
        weight:
            Edge weight (higher = stronger relationship).
        properties:
            Optional extra metadata.

        Returns
        -------
        GraphEdge
            The created edge.
        """
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            properties=properties or {},
        )
        return self._graph.add_edge(edge)

    def explore(
        self,
        start_id: str,
        depth: int = 3,
        mode: str = "bfs",
        relation_filter: str | None = None,
    ) -> GraphQueryResult:
        """Traverse the graph from *start_id*.

        Parameters
        ----------
        start_id:
            Node ID to begin traversal from.
        depth:
            Maximum traversal depth.
        mode:
            ``"bfs"`` or ``"dfs"``.
        relation_filter:
            If given, only follow edges matching this relation.

        Returns
        -------
        GraphQueryResult
            Reachable nodes and edges.
        """
        return self._graph.traverse(
            start_id=start_id,
            depth=depth,
            mode=mode,
            relation_filter=relation_filter,
        )

    def find_concepts(
        self,
        label: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphNode]:
        """Find concept nodes matching *label* and/or *agent_id*."""
        return self._graph.find_nodes(label=label, agent_id=agent_id, limit=limit)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Release resources held by the underlying stores."""
        self._graph.close()
        log.info("memory_manager.closed")
