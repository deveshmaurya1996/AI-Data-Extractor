from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models import UploadDataset, UploadDatasetRow
from logger import logger
from services import query_cache

MAX_ROWS_PER_UPLOADED_FILE = 5000


def _json_safe_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(k): _json_safe_cell(v) for k, v in row.items()}


def clear_conversation_uploads(db: Session, conversation_id: str) -> None:
    db.query(UploadDataset).filter(
        UploadDataset.conversation_id == conversation_id
    ).delete(synchronize_session=False)


def persist_conversation_uploads(
    db: Session,
    conversation_id: str,
    parsed_files: list[dict[str, Any]],
) -> list[str]:
    query_cache.invalidate_conversation(conversation_id)
    clear_conversation_uploads(db, conversation_id)
    dataset_ids: list[str] = []

    for item in parsed_files:
        rows_in = item.get("rows") or []
        capped = rows_in[:MAX_ROWS_PER_UPLOADED_FILE]
        fname = str(item.get("file") or "unknown")

        ds = UploadDataset(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            file_name=fname,
            row_count=len(capped),
            created_at=datetime.utcnow(),
        )
        db.add(ds)
        db.flush()

        for i, row in enumerate(capped):
            db.add(
                UploadDatasetRow(
                    dataset_id=ds.id,
                    row_index=i,
                    data=json_safe_row(row),
                )
            )
        dataset_ids.append(str(ds.id))

    return dataset_ids


def conversation_has_uploads(db: Session, conversation_id: str | None) -> bool:
    if not conversation_id or not str(conversation_id).strip():
        return False
    return (
        db.query(UploadDataset.id)
        .filter(UploadDataset.conversation_id == conversation_id.strip())
        .first()
        is not None
    )


def log_upload_stats(db: Session, conversation_id: str) -> dict[str, Any]:
    try:
        n_ds = (
            db.query(UploadDataset)
            .filter(UploadDataset.conversation_id == conversation_id)
            .count()
        )
        n_rows = (
            db.query(UploadDatasetRow)
            .join(UploadDataset, UploadDatasetRow.dataset_id == UploadDataset.id)
            .filter(UploadDataset.conversation_id == conversation_id)
            .count()
        )
        return {"datasets": n_ds, "rows": n_rows}
    except Exception as e:
        logger.warning("upload_stats: %s", e)
        return {"datasets": 0, "rows": 0}
