"""Tests for GraphMemory and MemoryManager (graph operations only).

VectorMemory tests require ChromaDB + embedding models; they are skipped
when ChromaDB is not installed to keep the test suite fast in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_memory.graph import GraphMemory
from hermes_memory.schemas import GraphEdge, GraphNode


# ─────────────────────────── GraphMemory ───────────────────────────────────


class TestGraphMemory:
    def test_add_and_get_node(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        node = gm.add_node(GraphNode(label="concept", properties={"name": "AI"}))
        fetched = gm.get_node(node.id)
        assert fetched is not None
        assert fetched.label == "concept"
        assert fetched.properties["name"] == "AI"
        gm.close()

    def test_get_missing_node_returns_none(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        assert gm.get_node("nonexistent-id") is None
        gm.close()

    def test_delete_node(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        node = gm.add_node(GraphNode(label="x"))
        assert gm.delete_node(node.id) is True
        assert gm.get_node(node.id) is None
        gm.close()

    def test_delete_missing_node(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        assert gm.delete_node("ghost") is False
        gm.close()

    def test_add_and_query_edge(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        a = gm.add_node(GraphNode(label="A"))
        b = gm.add_node(GraphNode(label="B"))
        edge = gm.add_edge(
            GraphEdge(source_id=a.id, target_id=b.id, relation="connects_to")
        )
        edges = gm.get_edges(source_id=a.id)
        assert len(edges) == 1
        assert edges[0].relation == "connects_to"
        assert edges[0].target_id == b.id
        gm.close()

    def test_delete_edge(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        a = gm.add_node(GraphNode(label="A"))
        b = gm.add_node(GraphNode(label="B"))
        edge = gm.add_edge(GraphEdge(source_id=a.id, target_id=b.id, relation="r"))
        assert gm.delete_edge(edge.id) is True
        assert gm.get_edges(source_id=a.id) == []
        gm.close()

    def test_bfs_traversal(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        root = gm.add_node(GraphNode(label="root"))
        child1 = gm.add_node(GraphNode(label="child"))
        child2 = gm.add_node(GraphNode(label="child"))
        grandchild = gm.add_node(GraphNode(label="grandchild"))
        gm.add_edge(GraphEdge(source_id=root.id, target_id=child1.id, relation="has"))
        gm.add_edge(GraphEdge(source_id=root.id, target_id=child2.id, relation="has"))
        gm.add_edge(
            GraphEdge(source_id=child1.id, target_id=grandchild.id, relation="has")
        )

        result = gm.traverse(root.id, depth=2, mode="bfs")
        node_ids = {n.id for n in result.nodes}
        assert root.id in node_ids
        assert child1.id in node_ids
        assert child2.id in node_ids
        assert grandchild.id in node_ids
        gm.close()

    def test_dfs_traversal(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        a = gm.add_node(GraphNode(label="A"))
        b = gm.add_node(GraphNode(label="B"))
        c = gm.add_node(GraphNode(label="C"))
        gm.add_edge(GraphEdge(source_id=a.id, target_id=b.id, relation="r"))
        gm.add_edge(GraphEdge(source_id=b.id, target_id=c.id, relation="r"))

        result = gm.traverse(a.id, depth=3, mode="dfs")
        node_ids = {n.id for n in result.nodes}
        assert {a.id, b.id, c.id} == node_ids
        gm.close()

    def test_traversal_depth_limit(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        nodes = [gm.add_node(GraphNode(label=f"n{i}")) for i in range(5)]
        for i in range(4):
            gm.add_edge(
                GraphEdge(source_id=nodes[i].id, target_id=nodes[i + 1].id, relation="r")
            )
        result = gm.traverse(nodes[0].id, depth=2)
        # Should include n0, n1, n2 — not n3 or n4.
        node_ids = {n.id for n in result.nodes}
        assert nodes[0].id in node_ids
        assert nodes[1].id in node_ids
        assert nodes[2].id in node_ids
        assert nodes[3].id not in node_ids
        gm.close()

    def test_relation_filter(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        a = gm.add_node(GraphNode(label="A"))
        b = gm.add_node(GraphNode(label="B"))
        c = gm.add_node(GraphNode(label="C"))
        gm.add_edge(GraphEdge(source_id=a.id, target_id=b.id, relation="good"))
        gm.add_edge(GraphEdge(source_id=a.id, target_id=c.id, relation="bad"))

        result = gm.traverse(a.id, depth=1, relation_filter="good")
        node_ids = {n.id for n in result.nodes}
        assert b.id in node_ids
        assert c.id not in node_ids
        gm.close()

    def test_find_nodes_by_label(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        gm.add_node(GraphNode(label="person", properties={"name": "Alice"}))
        gm.add_node(GraphNode(label="person", properties={"name": "Bob"}))
        gm.add_node(GraphNode(label="tool", properties={"name": "hammer"}))

        persons = gm.find_nodes(label="person")
        assert len(persons) == 2
        tools = gm.find_nodes(label="tool")
        assert len(tools) == 1
        gm.close()

    def test_invalid_traversal_mode(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        node = gm.add_node(GraphNode(label="x"))
        with pytest.raises(ValueError):
            gm.traverse(node.id, mode="invalid")
        gm.close()

    def test_cascade_delete_edges(self, tmp_path: Path) -> None:
        gm = GraphMemory(tmp_path / "graph.db")
        a = gm.add_node(GraphNode(label="A"))
        b = gm.add_node(GraphNode(label="B"))
        gm.add_edge(GraphEdge(source_id=a.id, target_id=b.id, relation="r"))
        gm.delete_node(a.id)
        # Edge should be cascade-deleted.
        edges = gm.get_edges(source_id=a.id)
        assert edges == []
        gm.close()


# ─────────────────────────── MemoryManager ─────────────────────────────────


class TestMemoryManagerGraph:
    """Tests for the graph portion of MemoryManager (no ChromaDB needed)."""

    def test_add_concept_and_link(self, tmp_path: Path) -> None:
        from hermes_memory.manager import MemoryManager

        # We test graph ops only; skip vector (ChromaDB) by not calling remember().
        mm = MemoryManager.__new__(MemoryManager)
        mm._base = tmp_path
        from hermes_memory.graph import GraphMemory

        mm._graph = GraphMemory(tmp_path / "graph.db")

        node_a = mm.add_concept("tool", {"name": "hammer"}, agent_id="a1")
        node_b = mm.add_concept("material", {"name": "nail"}, agent_id="a1")
        edge = mm.link(node_a.id, node_b.id, relation="uses")
        assert edge.relation == "uses"

        result = mm.explore(node_a.id, depth=1)
        node_ids = {n.id for n in result.nodes}
        assert node_a.id in node_ids
        assert node_b.id in node_ids
        mm._graph.close()
