
from __future__ import annotations

from collections.abc import Awaitable, Callable

from ai.plan_sql_builder import build_sql_from_plan
from ai.query_plan import PlanIntent, QueryPlan

from services._responses import llm_clarification_response

from ._types import SqlPlanningResult

_GenerateFn = Callable[..., Awaitable[str]]


def build_upload_preview_sql(cid_scope: str) -> SqlPlanningResult:
    out = SqlPlanningResult()
    out.sql_result = build_sql_from_plan(
        QueryPlan(
            intent=PlanIntent.UPLOAD_DATASET_PREVIEW,
            conversation_id=cid_scope,
        )
    )
    out.data_narrative_kind = "upload_dataset_preview"
    return out


async def guarded_upload_preview_from_plan(
    user_query: str,
    cid_scope: str,
    *,
    has_uploads: bool,
    spoken_name: str | None,
    generate_narrative: _GenerateFn,
) -> SqlPlanningResult:
    if not has_uploads:
        out = SqlPlanningResult()
        out.chat_response = await llm_clarification_response(
            user_query,
            reason_code="uploads_required_but_missing",
            detail=(
                "user asked to preview uploaded files but no "
                "CSV/Excel has been uploaded in this chat yet"
            ),
            spoken_name=spoken_name,
            generate_narrative=generate_narrative,
        )
        return out
    result = build_upload_preview_sql(cid_scope)
    return result

