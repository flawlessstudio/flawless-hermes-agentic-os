"""GraphMemory — SQLite-backed directed property graph.

Nodes and edges are stored in SQLite tables with JSON properties.
Traversal supports both BFS and DFS up to a configurable depth limit.

Usage::

    gm = GraphMemory("/tmp/hermes/graph.db")
    node_a = gm.add_node(GraphNode(label="concept", properties={"name": "AI"}))
    node_b = gm.add_node(GraphNode(label="concept", properties={"name": "ML"}))
    gm.add_edge(GraphEdge(source_id=node_a.id, target_id=node_b.id, relation="parent_of"))
    result = gm.traverse(node_a.id, depth=2)
"""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from pathlib import Path

import structlog

from hermes_memory.schemas import GraphEdge, GraphNode, GraphQueryResult

log = structlog.get_logger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id         TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    properties TEXT NOT NULL DEFAULT '{}',
    agent_id   TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_nodes_agent ON nodes(agent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);

CREATE TABLE IF NOT EXISTS edges (
    id         TEXT PRIMARY KEY,
    source_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation   TEXT NOT NULL,
    weight     REAL NOT NULL DEFAULT 1.0,
    properties TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
"""


class GraphMemory:
    """Directed property graph stored in SQLite.

    Nodes have a ``label`` and a JSON ``properties`` bag.
    Edges have a ``relation`` type, a ``weight``, and an optional properties bag.

    Parameters
    ----------
    path:
        Path to the SQLite database file.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._apply_schema()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()

    # ------------------------------------------------------------------ #
    # Node API                                                             #
    # ------------------------------------------------------------------ #

    def add_node(self, node: GraphNode) -> GraphNode:
        """Insert or replace a node.

        Parameters
        ----------
        node:
            The :class:`GraphNode` to upsert.

        Returns
        -------
        GraphNode
            The node as stored (same object).
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO nodes (id, label, properties, agent_id)
                VALUES (?, ?, ?, ?)
                """,
                (node.id, node.label, json.dumps(node.properties), node.agent_id),
            )
        log.debug("graph.node_added", id=node.id, label=node.label)
        return node

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by ID, or ``None`` if not found."""
        row = self._conn.execute(
            "SELECT id, label, properties, agent_id FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return self._row_to_node(row) if row else None

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges (cascade).

        Returns
        -------
        bool
            ``True`` if the node existed.
        """
        with self._conn:
            cur = self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return cur.rowcount > 0

    def find_nodes(
        self,
        label: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphNode]:
        """Find nodes filtered by *label* and/or *agent_id*."""
        clauses: list[str] = []
        params: list[str | int] = []
        if label:
            clauses.append("label = ?")
            params.append(label)
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # Clauses are built from a fixed allowlist of column names — no user data interpolated.
        query = "SELECT id, label, properties, agent_id FROM nodes " + where + " LIMIT ?"  # noqa: S608
        rows = self._conn.execute(query, (*params, limit)).fetchall()
        return [self._row_to_node(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Edge API                                                             #
    # ------------------------------------------------------------------ #

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """Insert or replace a directed edge.

        Parameters
        ----------
        edge:
            The :class:`GraphEdge` to upsert.  Source and target nodes must
            already exist.

        Returns
        -------
        GraphEdge
            The edge as stored.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO edges
                    (id, source_id, target_id, relation, weight, properties)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.relation,
                    edge.weight,
                    json.dumps(edge.properties),
                ),
            )
        log.debug(
            "graph.edge_added",
            id=edge.id,
            relation=edge.relation,
            src=edge.source_id,
            dst=edge.target_id,
        )
        return edge

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relation: str | None = None,
    ) -> list[GraphEdge]:
        """Retrieve edges matching the given filters."""
        clauses: list[str] = []
        params: list[str] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id = ?")
            params.append(target_id)
        if relation:
            clauses.append("relation = ?")
            params.append(relation)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # Clauses are built from a fixed allowlist of column names — no user data interpolated.
        query = "SELECT id, source_id, target_id, relation, weight, properties FROM edges " + where  # noqa: S608
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge by ID."""
        with self._conn:
            cur = self._conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    # Traversal                                                            #
    # ------------------------------------------------------------------ #

    def traverse(
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
            Node ID to start from.
        depth:
            Maximum number of hops to follow.
        mode:
            ``"bfs"`` (breadth-first) or ``"dfs"`` (depth-first).
        relation_filter:
            If given, only follow edges with this ``relation``.

        Returns
        -------
        GraphQueryResult
            All reachable nodes and edges within *depth* hops.
        """
        if mode not in ("bfs", "dfs"):
            raise ValueError(f"mode must be 'bfs' or 'dfs', got {mode!r}")

        visited_nodes: dict[str, GraphNode] = {}
        visited_edges: dict[str, GraphEdge] = {}

        # Queue/stack items are (node_id, current_depth)
        frontier: deque[tuple[str, int]] = deque()
        frontier.append((start_id, 0))

        while frontier:
            node_id, current_depth = frontier.popleft() if mode == "bfs" else frontier.pop()
            if node_id in visited_nodes:
                continue
            node = self.get_node(node_id)
            if node is None:
                continue
            visited_nodes[node_id] = node

            if current_depth >= depth:
                continue

            edges = self.get_edges(source_id=node_id, relation=relation_filter)
            for edge in edges:
                if edge.id not in visited_edges:
                    visited_edges[edge.id] = edge
                if edge.target_id not in visited_nodes:
                    frontier.append((edge.target_id, current_depth + 1))

        return GraphQueryResult(
            nodes=list(visited_nodes.values()),
            edges=list(visited_edges.values()),
            depth=depth,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _apply_schema(self) -> None:
        with self._conn:
            self._conn.executescript(_SCHEMA_SQL)

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> GraphNode:
        return GraphNode(
            id=row["id"],
            label=row["label"],
            properties=json.loads(row["properties"]),
            agent_id=row["agent_id"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> GraphEdge:
        return GraphEdge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation=row["relation"],
            weight=float(row["weight"]),
            properties=json.loads(row["properties"]),
        )
