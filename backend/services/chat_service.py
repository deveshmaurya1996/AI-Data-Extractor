from __future__ import annotations

import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ai.interfaces import ChatResponse
from logger import logger
from services.file_preview import build_upload_preview
from services.nl_query_pipeline import NLQueryPipeline
from services.upload_persist import (
    MAX_ROWS_PER_UPLOADED_FILE,
    log_upload_stats,
    persist_conversation_uploads,
)


class ChatService:
    def __init__(self) -> None:
        self._nl = NLQueryPipeline()

    async def handle_query(
        self,
        user_query: str,
        db: Session,
        conversation_id: str | None = None,
        clarification_selection: dict[str, object] | None = None,
    ) -> ChatResponse:
        return await self._nl.run(
            db,
            user_query,
            conversation_id=conversation_id,
            clarification_selection=clarification_selection,
        )

    async def handle_file_query(
        self,
        user_query: str,
        uploaded_files: list[UploadFile],
        db: Session,
        conversation_id: str | None,
    ) -> ChatResponse:
        parsed, parsing_errors, combined_preview = await build_upload_preview(
            uploaded_files, user_query
        )

        cid = (conversation_id or "").strip() or str(uuid.uuid4())

        metadata: dict[str, Any] = {
            "conversation_id": cid,
            "uploaded_files": [p["file"] for p in parsed],
            "files_processed": len(parsed),
            "files_failed": len(parsing_errors),
            "total_rows": sum(int(p["row_count"]) for p in parsed),
            "columns_by_file": {p["file"]: p["columns"] for p in parsed},
            "parsing_errors": parsing_errors,
            "query": user_query,
            "mode": "upload_persisted",
            "max_stored_rows_per_file": MAX_ROWS_PER_UPLOADED_FILE,
        }

        if not parsed:
            return ChatResponse(
                type="error",
                message=(
                    "I couldn't parse the uploaded file(s). "
                    "Please upload CSV, Excel, JSON, or TXT files."
                ),
                suggestions=["Try uploading a valid CSV or XLSX file with headers."],
            )

        try:
            dataset_ids = persist_conversation_uploads(db, cid, parsed)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("upload_persist_failed")
            return ChatResponse(
                type="error",
                message=(
                    "The file was parsed but could not be saved to the database. "
                    "Check the server logs and database connection."
                ),
                suggestions=["Try a smaller file or fewer rows, then upload again."],
            )

        stats = log_upload_stats(db, cid)
        metadata["dataset_ids"] = dataset_ids
        metadata["stored_dataset_count"] = stats["datasets"]
        metadata["stored_row_count"] = stats["rows"]
        truncated = any(
            int(p["row_count"]) > MAX_ROWS_PER_UPLOADED_FILE for p in parsed
        )
        metadata["truncated_to_max_rows"] = truncated

        return ChatResponse(
            type="success",
            message=(
                f"Saved {len(parsed)} file(s) ({stats['rows']} row(s) in this chat). "
                "Ask questions about the uploaded data in natural language."
            ),
            data=combined_preview,
            metadata=metadata,
        )
