"""Pydantic schemas for the hermes_memory package."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single piece of memory stored in the vector store."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_id: str = ""
    embedding: list[float] | None = None


class MemoryQueryResult(BaseModel):
    """Result of a vector similarity search."""

    entry: MemoryEntry
    distance: float
    relevance_score: float  # 1.0 - distance (for cosine)


class GraphNode(BaseModel):
    """A node in the graph memory."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    agent_id: str = ""


class GraphEdge(BaseModel):
    """A directed edge in the graph memory."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResult(BaseModel):
    """Result of a graph traversal."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    depth: int
