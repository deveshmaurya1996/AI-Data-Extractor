"""Semantic fast-path + classifier / LLM SQL planning (split from NLQueryPipeline)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ai.classifier import IntentClassifier
from ai.interfaces import EntityExtractionResult
from ai.narrative_generator import NarrativeKind
from ai.plan_generator import PlanGenerator
from ai.semantic_intent_router import SemanticIntent, SemanticRoute

from .customer_360 import semantic_customer_360_sql
from .llm_plan import generate_plan_and_sql
from .sample_overview import build_sample_overview_sql
from .templates import try_classifier_sql
from .upload_preview import build_upload_preview_sql
from ._types import SqlPlanningResult

_GenerateFn = Callable[..., Awaitable[str]]
_ClassifyConvFn = Callable[[str], NarrativeKind]
_NoteConvFn = Callable[[str | None], None]


def try_semantic_sql(
    sem: SemanticRoute,
    entities: EntityExtractionResult,
    cid_scope: str,
) -> SqlPlanningResult:
    if sem.intent == SemanticIntent.CUSTOMER_360:
        return semantic_customer_360_sql(entities, cid_scope)
    if sem.intent == SemanticIntent.SAMPLE_DATA_OVERVIEW:
        return build_sample_overview_sql()
    if sem.intent == SemanticIntent.UPLOAD_DATASET_PREVIEW:
        return build_upload_preview_sql(cid_scope)
    return SqlPlanningResult()


async def plan_classifier_or_llm_sql(
    db: Any,
    classifier: IntentClassifier,
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

    classification = classifier.classify(
        normalized_query,
        has_customer=bool(entities.customer_candidates),
        has_time_period=bool(entities.time_period),
    )
    tpl = try_classifier_sql(classification, entities, has_uploads)
    if tpl is not None:
        return tpl

    return await generate_plan_and_sql(
        db,
        plan_generator,
        normalized_query=normalized_query,
        user_query=user_query,
        entities=entities,
        cid_scope=cid_scope,
        has_uploads=has_uploads,
        generate_narrative=generate_narrative,
        classify_conversational_kind=classify_conversational_kind,
        note_conversational_turn=note_conversational_turn,
    )


__all__ = ["SqlPlanningResult", "plan_classifier_or_llm_sql", "try_semantic_sql"]
