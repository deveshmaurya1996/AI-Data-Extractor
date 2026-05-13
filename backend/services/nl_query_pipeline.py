"""Natural-language query orchestration — wiring extraction, planning, and execution."""

from __future__ import annotations

import time
from typing import Any

from ai.classifier import IntentClassifier
from ai.conversation_router import (
    classify_conversational_kind,
    is_not_a_data_question_sql,
    should_respond_conversationally,
)
from ai.entity_extractor import EntityExtractor
from ai.executor import QueryExecutor
from ai.followup_summarizer import summarize_last_tabular_answer_async
from ai.formatter import ResponseFormatter
from ai.interfaces import ChatResponse, SQLGenerationResult
from ai.narrative_generator import NarrativeKind, generate_narrative
from ai.plan_generator import PlanGenerator
from ai.query_normalizer import normalize_query_for_extraction
from ai.semantic_intent_router import route_semantic_intent
from ai.validator import SQLValidator
from logger import logger
from services import conversation_context as conv_ctx
from services import query_cache
from services._pipeline_helpers import (
    apply_customer_clarification,
    customer_id_for_template,
)
from services._responses import DEFAULT_SUGGESTIONS
from services._responses import _friendly_error_message
from services._responses import _KNOWN_CUSTOMER_EXAMPLES
from services._responses import conversational_chat_response as conversational_chat_svc
from services._responses import llm_clarification_response as llm_clarification_svc
from services._responses import llm_narrator_failed_response
from services._responses import plain_followup_response
from services._responses import validation_error_response

from services._query_handlers.sql_planning import (
    plan_classifier_or_llm_sql,
    try_semantic_sql,
)


async def _llm_clarification_response(
    user_query: str,
    *,
    reason_code: str,
    detail: str,
    spoken_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> ChatResponse:
    """Delegate to `_responses`; uses module-level `generate_narrative` (patchable)."""
    return await llm_clarification_svc(
        user_query,
        reason_code=reason_code,
        detail=detail,
        spoken_name=spoken_name,
        extra_metadata=extra_metadata,
        generate_narrative=generate_narrative,
    )


async def _conversational_chat_response(
    user_query: str, conversation_id: str | None = None
) -> ChatResponse:
    return await conversational_chat_svc(
        user_query,
        conversation_id,
        generate_narrative=generate_narrative,
        classify_conversational_kind=classify_conversational_kind,
        note_conversational_turn=conv_ctx.note_conversational_turn,
    )


_customer_id_for_template = customer_id_for_template


class NLQueryPipeline:
    def __init__(self) -> None:
        self._classifier = IntentClassifier()
        self._plan_generator = PlanGenerator()
        self._validator = SQLValidator()
        self._formatter = ResponseFormatter()

    async def run(
        self,
        db: Any,
        user_query: str,
        conversation_id: str | None = None,
        clarification_selection: dict[str, Any] | None = None,
    ) -> ChatResponse:
        try:
            cid_scope = (conversation_id or "").strip()
            conv_ctx.append_user_turn(cid_scope, user_query)

            normalized_query = normalize_query_for_extraction(user_query)
            entities = EntityExtractor(db).extract(normalized_query)
            entities = apply_customer_clarification(entities, clarification_selection)
            entities = conv_ctx.apply_context_to_entities(
                cid_scope, entities, normalized_query
            )
            conv_ctx.note_customer_from_entities(cid_scope, entities)

            if conv_ctx.wants_plain_language_followup(cid_scope, normalized_query):
                snap = conv_ctx.snapshot_for_plain_followup(cid_scope)
                if snap:
                    prior_q, rows_n, sample = snap
                    try:
                        msg = await summarize_last_tabular_answer_async(
                            follow_up_question=user_query,
                            prior_user_question=prior_q,
                            row_count=rows_n,
                            sample_rows=sample,
                        )
                    except Exception as e:
                        return llm_narrator_failed_response(e)
                    conv_ctx.note_plain_followup_turn(cid_scope)
                    return plain_followup_response(msg)

            if entities.requires_clarification and entities.customer_candidates:
                sugg: list[dict[str, object]] = []
                for c in entities.customer_candidates:
                    row: dict[str, object] = {
                        "id": c["id"],
                        "name": c["name"],
                        "schema": c["schema"],
                    }
                    em = c.get("email")
                    if em:
                        row["email"] = em
                    sugg.append(row)
                return ChatResponse(
                    type="clarification",
                    message=(
                        f"I found {len(entities.customer_candidates)} customers matching "
                        f"'{entities.customer_name}'. Which one did you mean?"
                    ),
                    suggestions=sugg,
                    metadata={"conversation_id": cid_scope or None},
                )

            if should_respond_conversationally(
                normalized_query, entities, conversation_id=cid_scope
            ):
                return await _conversational_chat_response(user_query, cid_scope)

            from services.upload_persist import conversation_has_uploads

            has_uploads = conversation_has_uploads(db, cid_scope)

            sem = route_semantic_intent(
                normalized_query, entities, has_uploads=has_uploads
            )

            sql_result: SQLGenerationResult | None = None
            data_narrative_kind: NarrativeKind | None = None

            planned = try_semantic_sql(sem, entities, cid_scope)
            if planned.chat_response is not None:
                return planned.chat_response
            if planned.sql_result is not None:
                sql_result = planned.sql_result
                data_narrative_kind = planned.data_narrative_kind

            if sql_result is None:
                planned_llm = await plan_classifier_or_llm_sql(
                    db,
                    self._classifier,
                    self._plan_generator,
                    normalized_query=normalized_query,
                    user_query=user_query,
                    entities=entities,
                    cid_scope=cid_scope,
                    has_uploads=has_uploads,
                    generate_narrative=generate_narrative,
                    classify_conversational_kind=classify_conversational_kind,
                    note_conversational_turn=conv_ctx.note_conversational_turn,
                )
                if planned_llm.chat_response is not None:
                    return planned_llm.chat_response
                sql_result = planned_llm.sql_result
                if planned_llm.data_narrative_kind is not None:
                    data_narrative_kind = planned_llm.data_narrative_kind

            if sql_result is None:
                logger.error("nl_query_pipeline: sql_result unset after planning")
                return ChatResponse(
                    type="error",
                    message=_friendly_error_message(None, "unknown"),
                    suggestions=DEFAULT_SUGGESTIONS,
                )

            if not sql_result.success or not sql_result.sql:
                logger.warning("sql_generation_failed: %s", sql_result.error)
                return ChatResponse(
                    type="error",
                    message=_friendly_error_message(
                        sql_result.error, "sql_generation"
                    ),
                    suggestions=DEFAULT_SUGGESTIONS,
                )

            if is_not_a_data_question_sql(sql_result.sql):
                return await _conversational_chat_response(user_query, cid_scope)

            validation = self._validator.validate(sql_result.sql)
            if not validation.is_safe:
                logger.warning(
                    "sql_validation_failed: reason=%s error=%s",
                    validation.reason,
                    validation.error,
                )
                return validation_error_response(validation, sql_result.sql)

            sql_safe = validation.sql_safe or ""
            t0 = time.perf_counter()
            cached = query_cache.get_cached(cid_scope or None, sql_safe)
            if cached is not None:
                data = cached
                cache_hit = True
            else:
                execution = QueryExecutor(db).execute(sql_safe)
                if not execution.success:
                    logger.warning("sql_execution_failed: %s", execution.error)
                    return ChatResponse(
                        type="error",
                        message=_friendly_error_message(
                            execution.error, "execution"
                        ),
                        suggestions=DEFAULT_SUGGESTIONS,
                    )
                data = execution.data
                query_cache.set_cached(cid_scope or None, sql_safe, data)
                cache_hit = False

            exec_ms = (time.perf_counter() - t0) * 1000.0

            conv_ctx.note_sql_success(
                cid_scope,
                user_query=user_query,
                data=data,
                row_count=len(data),
                sql_safe=sql_safe,
                topic_hints=conv_ctx.topic_hints_from_entities(entities, user_query),
            )

            narrative_kind: NarrativeKind
            if not data:
                narrative_kind = "empty_result"
            elif data_narrative_kind is not None:
                narrative_kind = data_narrative_kind
            else:
                narrative_kind = "tabular_success"

            try:
                narrative_message = await generate_narrative(
                    narrative_kind,
                    user_query=user_query,
                    row_count=len(data),
                    sample_rows=data[:5],
                    strategy=sql_result.strategy.value,
                    sql=sql_result.sql,
                    used_uploads=has_uploads,
                )
            except Exception as e:
                return llm_narrator_failed_response(e)

            formatted = self._formatter.format(
                message=narrative_message,
                data=data,
                sql=sql_result.sql,
                strategy=sql_result.strategy.value,
                confidence=sql_result.confidence,
                used_uploads=has_uploads,
            )

            if not data:
                from services.recovery_suggestions import build_recovery_suggestions

                recovery = build_recovery_suggestions(db, user_query, entities)
            else:
                recovery = []

            meta = {
                **formatted.metadata,
                "execution_time_ms": round(exec_ms, 2),
                "cache_hit": cache_hit,
                "conversation_id": cid_scope or None,
                "narrative_kind": narrative_kind,
                "data_sources": (
                    ["uploads", "ecommerce", "support"]
                    if has_uploads
                    else ["ecommerce", "support"]
                ),
            }
            if recovery:
                meta["follow_up_suggestions"] = recovery

            out_message = formatted.message
            if recovery:
                out_message += "\n\nTry one of the suggested follow-ups below."

            return ChatResponse(
                type="success",
                message=out_message,
                data=formatted.data,
                metadata=meta,
            )

        except Exception as e:
            logger.exception("nl_query_pipeline_error")
            return ChatResponse(
                type="error",
                message=_friendly_error_message(str(e), "unknown"),
                suggestions=DEFAULT_SUGGESTIONS,
            )
