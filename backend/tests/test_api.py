from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from ai.interfaces import ChatResponse


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("db.engine.init_db", lambda: None)
    from main import app
    from api.routes import get_db

    def _db():
        db = MagicMock()
        yield db

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_schema_includes_uploads(client: TestClient):
    r = client.get("/api/schema")
    assert r.status_code == 200
    body = r.json()
    assert "uploads" in body
    assert "datasets" in body["uploads"]


def test_chat_post_mocked_pipeline(monkeypatch, client: TestClient):
    from api.routes import chat_service

    monkeypatch.setattr(
        chat_service,
        "handle_query",
        AsyncMock(
            return_value=ChatResponse(
                type="success",
                message="ok",
                data=[{"n": 1}],
                metadata={"row_count": 1},
            )
        ),
    )
    r = client.post(
        "/api/chat",
        json={"query": "hello", "conversation_id": "00000000-0000-4000-8000-000000000001"},
    )
    assert r.status_code == 200
    assert r.json()["type"] == "success"
    assert r.json()["message"] == "ok"


def test_chat_post_passes_clarification_selection(monkeypatch, client: TestClient):
    from api.routes import chat_service

    mock = AsyncMock(
        return_value=ChatResponse(
            type="success",
            message="done",
            data=[],
            metadata={},
        )
    )
    monkeypatch.setattr(chat_service, "handle_query", mock)
    sel = {"id": 3, "name": "Pat", "schema": "ecommerce"}
    r = client.post(
        "/api/chat",
        json={
            "query": "orders for Pat",
            "conversation_id": "00000000-0000-4000-8000-000000000002",
            "clarification_selection": sel,
        },
    )
    assert r.status_code == 200
    mock.assert_awaited_once()
    kwargs = mock.await_args.kwargs
    assert kwargs["clarification_selection"] == sel
