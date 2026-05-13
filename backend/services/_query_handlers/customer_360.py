
from __future__ import annotations

from collections.abc import Awaitable, Callable

from ai.interfaces import EntityExtractionResult
from ai.plan_sql_builder import build_sql_from_plan
from ai.query_plan import (
    QueryPlan,
    merge_entity_customer_context,
    query_plan_customer_360_from_entities,
)
from ai.semantic_intent_router import query_matches_sample_data_overview
from services._responses import llm_clarification_response

from .sample_overview import build_sample_overview_sql
from ._types import SqlPlanningResult

_GenerateFn = Callable[..., Awaitable[str]]


def semantic_customer_360_sql(
    entities: EntityExtractionResult,
    cid_scope: str,
) -> SqlPlanningResult:
    out = SqlPlanningResult()
    qp360 = query_plan_customer_360_from_entities(
        entities, conversation_id=cid_scope
    )
    if qp360 is not None:
        out.sql_result = build_sql_from_plan(qp360)
        out.data_narrative_kind = "customer_360"
    return out


async def merge_customer_360_llm_plan(
    user_query: str,
    normalized_query: str,
    entities: EntityExtractionResult,
    *,
    cid_scope: str,
    base: QueryPlan,
    generate_narrative: _GenerateFn,
) -> SqlPlanningResult:
    merged = merge_entity_customer_context(base, entities)
    if not (merged.canonical_customer_name or "").strip() and not (
        merged.canonical_customer_email or ""
    ).strip():
        if query_matches_sample_data_overview(normalized_query):
            return build_sample_overview_sql()
        out = SqlPlanningResult()
        out.chat_response = await llm_clarification_response(
            user_query,
            reason_code="customer_360_no_canonical",
            detail=(
                "user asked for a full customer overview "
                "but no single customer could be resolved "
                "from the database"
            ),
            spoken_name=entities.spoken_customer_term,
            generate_narrative=generate_narrative,
        )
        return out
    out = SqlPlanningResult()
    out.sql_result = build_sql_from_plan(merged)
    out.data_narrative_kind = "customer_360"
    return out
