"""Lightweight integration checks (no live Postgres required)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("db.engine.init_db", lambda: None)
    from main import app
    from api.routes import get_db

    def _db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_api_root_and_health(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "service" in r.json()

    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["status"] == "healthy"
