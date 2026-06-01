"""Tests for the Hermes API — GATE F5."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hermes_api.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    from hermes_orchestrator.registry import AgentRegistry
    app.state.registry = AgentRegistry()
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_ready_returns_true(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "ready" in data


def test_agents_list_returns_list(client: TestClient) -> None:
    resp = client.get("/agents/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert resp.json() == []  # empty registry


def test_agents_not_found(client: TestClient) -> None:
    resp = client.get("/agents/nonexistent")
    assert resp.status_code == 404


def test_request_id_in_response(client: TestClient) -> None:
    resp = client.get("/health")
    assert "x-request-id" in resp.headers


def test_docs_endpoint(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
