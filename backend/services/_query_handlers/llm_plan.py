"""Pollinations planner + `QueryPlan` intent dispatch (formerly inline in NLQueryPipeline)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ai.interfaces import ChatResponse, EntityExtractionResult
from ai.narrative_generator import NarrativeKind
from ai.plan_generator import PlanGenerator
from ai.query_plan import PlanIntent, QueryPlan
from ai.query_templates import TemplateQueryExecutor
from logger import logger
from services._pipeline_helpers import combined_sql_context
from services._responses import (
    DEFAULT_SUGGESTIONS,
    conversational_chat_response,
    llm_clarification_response,
)
from services._responses import _friendly_error_message

from .customer_360 import merge_customer_360_llm_plan
from .sample_overview import build_sample_overview_sql
from .templates import sql_from_registered_template
from .upload_preview import guarded_upload_preview_from_plan
from ._types import SqlPlanningResult


_GenerateFn = Callable[..., Awaitable[str]]
_ClassifyConvFn = Callable[[str], NarrativeKind]
_NoteConvFn = Callable[[str | None], None]


def _sql_generation_failure_response() -> ChatResponse:
    return ChatResponse(
        type="error",
        message=_friendly_error_message(None, "sql_generation"),
        suggestions=DEFAULT_SUGGESTIONS,
    )


@dataclass(frozen=True)
class _PlanDispatchContext:
    db: Any
    user_query: str
    normalized_query: str
    entities: EntityExtractionResult
    cid_scope: str
    has_uploads: bool
    generate_narrative: _GenerateFn
    classify_conversational_kind: _ClassifyConvFn
    note_conversational_turn: _NoteConvFn


async def _intent_unsupported(ctx: _PlanDispatchContext, _base: QueryPlan) -> SqlPlanningResult:
    from services.recovery_suggestions import build_recovery_suggestions

    recovery = build_recovery_suggestions(ctx.db, ctx.user_query, ctx.entities)
    extra: dict[str, Any] = {"error_kind": "unsupported_plan"}
    if recovery:
        extra["follow_up_suggestions"] = recovery
    out = SqlPlanningResult()
    out.chat_response = await llm_clarification_response(
        ctx.user_query,
        reason_code="unsupported_plan",
        detail=(
            "no safe deterministic plan; ask user to narrow "
            "to orders, tickets, or one specific customer"
        ),
        spoken_name=ctx.entities.spoken_customer_term,
        extra_metadata=extra,
        generate_narrative=ctx.generate_narrative,
    )
    return out


async def _intent_customer_360(ctx: _PlanDispatchContext, base: QueryPlan) -> SqlPlanningResult:
    return await merge_customer_360_llm_plan(
        ctx.user_query,
        ctx.normalized_query,
        ctx.entities,
        cid_scope=ctx.cid_scope,
        base=base,
        generate_narrative=ctx.generate_narrative,
    )


async def _intent_sample_overview(
    _ctx: _PlanDispatchContext, _base: QueryPlan
) -> SqlPlanningResult:
    return build_sample_overview_sql()


async def _intent_upload_preview(
    ctx: _PlanDispatchContext, _base: QueryPlan
) -> SqlPlanningResult:
    return await guarded_upload_preview_from_plan(
        ctx.user_query,
        ctx.cid_scope,
        has_uploads=ctx.has_uploads,
        spoken_name=ctx.entities.spoken_customer_term,
        generate_narrative=ctx.generate_narrative,
    )


async def _intent_template(ctx: _PlanDispatchContext, base: QueryPlan) -> SqlPlanningResult:
    if not base.template_key:
        out = SqlPlanningResult()
        out.chat_response = _sql_generation_failure_response()
        return out
    if base.template_key not in TemplateQueryExecutor.TEMPLATES:
        out = SqlPlanningResult()
        out.chat_response = await llm_clarification_response(
            ctx.user_query,
            reason_code="unknown_template",
            detail=(f"planner returned unknown template '{base.template_key}'"),
            spoken_name=ctx.entities.spoken_customer_term,
            generate_narrative=ctx.generate_narrative,
        )
        return out
    return sql_from_registered_template(base.template_key, ctx.entities)


_PLAN_HANDLERS: dict[
    PlanIntent,
    Callable[
        [_PlanDispatchContext, QueryPlan],
        Awaitable[SqlPlanningResult],
    ],
] = {
    PlanIntent.UNSUPPORTED: _intent_unsupported,
    PlanIntent.CUSTOMER_360: _intent_customer_360,
    PlanIntent.SAMPLE_DATA_OVERVIEW: _intent_sample_overview,
    PlanIntent.UPLOAD_DATASET_PREVIEW: _intent_upload_preview,
}


async def _dispatch_query_plan(
    ctx: _PlanDispatchContext,
    base: QueryPlan,
) -> SqlPlanningResult:
    if base.intent == PlanIntent.TEMPLATE:
        return await _intent_template(ctx, base)
    handler = _PLAN_HANDLERS.get(base.intent)
    if handler is None:
        out = SqlPlanningResult()
        out.chat_response = _sql_generation_failure_response()
        return out
    return await handler(ctx, base)


async def generate_plan_and_sql(
    db: Any,
    plan_generator: PlanGenerator,
    *,
    normalized_query: str,
    user_query: str,
    entities: EntityExtractionResult,
    cid_scope: str,
    has_uploads: bool,
    generate_narrative: _GenerateFn,
    classify_conversational_kind: _ClassifyConvFn,
    note_conversational_turn: _NoteConvFn,
) -> SqlPlanningResult:
    classify_fn = classify_conversational_kind
    note_fn = note_conversational_turn

    ctx = _PlanDispatchContext(
        db=db,
        user_query=user_query,
        normalized_query=normalized_query,
        entities=entities,
        cid_scope=cid_scope,
        has_uploads=has_uploads,
        generate_narrative=generate_narrative,
        classify_conversational_kind=classify_fn,
        note_conversational_turn=note_fn,
    )

    out = SqlPlanningResult()
    try:
        payload = await plan_generator.generate_async(
            user_query=normalized_query,
            entity_context=combined_sql_context(entities, cid_scope),
            has_uploads=has_uploads,
        )
    except ValueError as e:
        err_s = str(e).lower()
        if (
            "pollinations_api_key" in err_s
            or "not set" in err_s
            or "api key" in err_s
        ):
            out.chat_response = ChatResponse(
                type="error",
                message=_friendly_error_message(str(e), "sql_generation"),
                suggestions=DEFAULT_SUGGESTIONS,
            )
            return out
        if "invalid_llm_plan_json" in err_s:
            out.chat_response = await llm_clarification_response(
                user_query,
                reason_code="invalid_llm_plan_json",
                detail="planner returned malformed JSON",
                spoken_name=entities.spoken_customer_term,
                generate_narrative=generate_narrative,
            )
            return out
        raise
    except Exception as e:
        logger.warning("llm_plan_generation_failed: %s", e)
        out.chat_response = ChatResponse(
            type="error",
            message=_friendly_error_message(str(e), "sql_generation"),
            suggestions=DEFAULT_SUGGESTIONS,
        )
        return out

    if payload.intent == "not_a_data_question":
        out.chat_response = await conversational_chat_response(
            user_query,
            cid_scope,
            generate_narrative=generate_narrative,
            classify_conversational_kind=classify_fn,
            note_conversational_turn=note_fn,
        )
        return out

    base = payload.to_query_plan(conversation_id=cid_scope)
    return await _dispatch_query_plan(ctx, base)
