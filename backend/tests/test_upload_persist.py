from unittest.mock import MagicMock

from services import query_cache
from services.upload_persist import (
    clear_conversation_uploads,
    json_safe_row,
    persist_conversation_uploads,
)


def test_json_safe_row_serializes_dates():
    class D:
        def isoformat(self):
            return "2024-01-01"

    row = {"d": D(), "n": 3, "s": "x"}
    out = json_safe_row(row)
    assert out["d"] == "2024-01-01"
    assert out["n"] == 3


def test_clear_conversation_uploads_deletes_datasets():
    db = MagicMock()
    chain = MagicMock()
    db.query.return_value = chain
    chain.filter.return_value = chain
    chain.delete.return_value = 2

    clear_conversation_uploads(db, "cid-1")

    db.query.assert_called_once()
    chain.filter.assert_called_once()
    chain.delete.assert_called_once_with(synchronize_session=False)


def test_persist_invalidates_cache(monkeypatch):
    inv = MagicMock()
    monkeypatch.setattr(query_cache, "invalidate_conversation", inv)
    monkeypatch.setattr(
        "services.upload_persist.clear_conversation_uploads", MagicMock()
    )
    db = MagicMock()
    parsed = [
        {
            "file": "a.csv",
            "rows": [{"x": 1}],
            "row_count": 1,
            "columns": ["x"],
            "preview": [],
        }
    ]
    db.add = MagicMock()
    db.flush = MagicMock()

    persist_conversation_uploads(db, "conv-99", parsed)

    inv.assert_called_once_with("conv-99")
    assert db.add.called
    assert db.flush.called
