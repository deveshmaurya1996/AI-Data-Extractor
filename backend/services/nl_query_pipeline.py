
from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

from sqlalchemy.orm import Session

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
from ai.interfaces import (
    ChatResponse,
    EntityExtractionResult,
    SQLGenerationResult,
    ValidationResult,
)
from ai.narrative_generator import NarrativeKind, generate_narrative
from ai.plan_generator import PlanGenerator
from ai.plan_sql_builder import build_sql_from_plan
from ai.pg_interval import interval_sql
from ai.query_normalizer import normalize_query_for_extraction
from ai.query_plan import (
    PlanIntent,
    QueryPlan,
    merge_entity_customer_context,
    query_plan_customer_360_from_entities,
)
from ai.query_templates import TemplateQueryExecutor
from ai.semantic_intent_router import (
    SemanticIntent,
    query_matches_sample_data_overview,
    route_semantic_intent,
)
from ai.validator import SQLValidator, query_policy_lines
from logger import logger
from services import query_cache
from services import conversation_context as conv_ctx
from services.recovery_suggestions import build_recovery_suggestions
from services.upload_persist import conversation_has_uploads


def _friendly_error_message(raw: str | None, context: str) -> str:
    """Turn internal/API errors into short user-facing text (full detail stays in logs)."""
    if context == "llm_narrative":
        # Hard-fail message: the LLM is the only allowed narrator for user replies.
        # Without it we refuse to fabricate anything from Python strings.
        detail = ""
        if raw:
            low = raw.lower()
            if "pollinations_api_key" in low or "api key" in low or "not set" in low:
                detail = " The Pollinations API key is missing on the server."
            elif "401" in raw or "authentication" in low or "invalid api key" in low:
                detail = " The Pollinations API key was rejected as invalid."
            elif "insufficient_quota" in low or ("429" in raw and "quota" in low):
                detail = " The Pollinations account has no quota left."
            elif "rate" in low and "limit" in low:
                detail = " The Pollinations service is rate-limited."
        return (
            "The AI service did not return an answer, so I cannot reply right now."
            f"{detail} Check the Pollinations API key, quota, and connectivity in "
            "the backend configuration, then ask again."
        )
    if not raw:
        return (
            "Something went wrong while processing your question. "
            "Try again or pick one of the suggested questions."
        )
    lower = raw.lower()
    if "insufficient_quota" in lower or (
        "429" in raw and "quota" in lower
    ):
        return (
            "The AI provider has no quota left for your account, so open-ended "
            "questions cannot run. Check your Pollinations (or LLM) plan and API key, "
            "or ask a question that matches a built-in example (orders, tickets, customers)."
        )
    if "rate" in lower and "limit" in lower:
        return "The AI service is rate-limited. Wait a few seconds and try again."
    if "authentication" in lower or "invalid api key" in lower or "401" in raw:
        return (
            "The server could not authenticate with the AI provider. "
            "Check the API key in the backend configuration."
        )
    if context == "sql_generation":
        return (
            "We could not build a safe query for that question. "
            "Try rephrasing it, or use one of the suggested questions below."
        )
    if context == "execution":
        return (
            "The query could not be run against the database. "
            "Try a simpler question or one of the suggestions below."
        )
    if context == "unknown":
        return (
            "An unexpected error occurred. Try again or use one of the suggested questions."
        )
    return (
        "Something went wrong. Try a different question or use one of the suggestions below."
    )


DEFAULT_SUGGESTIONS = [
    "Show me all orders from customer Hina Patel in the last month",
    "List all open support tickets for customer Ben Okafor",
    "What is the total order value for each customer who has opened support tickets?",
    "Find customers who have made purchases but never raised support tickets",
]


def _truncate_sql_preview(sql: str | None, max_chars: int = 800) -> str | None:
    if not sql or not sql.strip():
        return None
    s = sql.strip()
    if len(s) <= max_chars:
        return s
    return f"{s[:max_chars]}…"


def _validation_error_response(
    validation: ValidationResult,
    generated_sql: str | None,
) -> ChatResponse:
    preview = _truncate_sql_preview(generated_sql)
    policy = query_policy_lines()
    meta: dict[str, Any] = {
        "error_kind": "query_validation",
        "validation_reason": validation.reason,
        "validation_error": validation.error or "",
        "sql_preview": preview,
        "what_you_can_ask": policy,
    }
    lines = [
        "The generated SQL did not pass read-only safety checks, so it was not run.",
        "",
        f"What was wrong: {validation.reason}",
    ]
    err = (validation.error or "").strip()
    if err and err != validation.reason:
        lines.extend(["", f"Additional detail: {err}"])
    if preview:
        lines.extend(["", "SQL preview (what the model produced, truncated):"])
        lines.append(preview)
    lines.extend(["", "What you can ask here:"])
    lines.extend(f"• {item}" for item in policy)
    return ChatResponse(
        type="error",
        message="\n".join(lines),
        suggestions=DEFAULT_SUGGESTIONS,
        metadata=meta,
    )


def _combined_sql_context(
    entities: EntityExtractionResult, conversation_id: str | None
) -> str | None:
    chunks: list[str] = []
    tx = conv_ctx.transcript_block_for_sql(conversation_id)
    if tx:
        chunks.append("Conversation thread context:\n" + tx)
    ent = _entity_sql_hint(entities)
    if ent:
        chunks.append(ent)
    if not chunks:
        return None
    return "\n\n".join(chunks)


def _plain_followup_response(message: str) -> ChatResponse:
    return ChatResponse(
        type="success",
        message=message,
        data=[],
        metadata={
            "response_mode": "plain_followup",
            "skip_sql": True,
            "strategy": "context_summary",
            "confidence": 0.85,
            "confidence_label": "medium",
            "row_count": 0,
            "explanation": "Plain-language follow-up on the last tabular answer.",
            "data_preview": [],
            "used_uploads": False,
        },
    )


def _llm_narrator_failed_response(exc: BaseException) -> ChatResponse:
    logger.warning("narrative_generator_failed: %s", exc, exc_info=True)
    return ChatResponse(
        type="error",
        message=_friendly_error_message(str(exc), "llm_narrative"),
        suggestions=DEFAULT_SUGGESTIONS,
        metadata={"error_kind": "llm_narrator_unavailable"},
    )


_KNOWN_CUSTOMER_EXAMPLES: tuple[str, ...] = (
    "Alice Chen",
    "Ben Okafor",
    "Hina Patel",
)


async def _llm_clarification_response(
    user_query: str,
    *,
    reason_code: str,
    detail: str,
    spoken_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> ChatResponse:
    ctx: dict[str, Any] = {
        "reason_code": reason_code,
        "detail": detail,
        "available_schemas": ["ecommerce", "support"],
        "known_customer_examples": list(_KNOWN_CUSTOMER_EXAMPLES),
    }
    if spoken_name:
        ctx["spoken_name"] = spoken_name
    try:
        message = await generate_narrative(
            "needs_clarification",
            user_query=user_query,
            clarification_context=ctx,
        )
    except Exception as e:
        return _llm_narrator_failed_response(e)

    meta: dict[str, Any] = {
        "response_mode": "clarification",
        "skip_sql": True,
        "narrative_kind": "needs_clarification",
        "clarification_reason": reason_code,
    }
    if extra_metadata:
        meta.update(extra_metadata)
    return ChatResponse(
        type="clarification",
        message=message,
        suggestions=list(DEFAULT_SUGGESTIONS),
        metadata=meta,
    )


async def _conversational_chat_response(
    user_query: str, conversation_id: str | None = None
) -> ChatResponse:
    kind: NarrativeKind = classify_conversational_kind(user_query)
    try:
        message = await generate_narrative(kind, user_query=user_query)
    except Exception as e:
        return _llm_narrator_failed_response(e)

    conv_ctx.note_conversational_turn(conversation_id)
    return ChatResponse(
        type="success",
        message=message,
        data=[],
        metadata={
            "response_mode": "conversational",
            "skip_sql": True,
            "strategy": "conversational",
            "confidence": 1.0,
            "confidence_label": "high",
            "row_count": 0,
            "explanation": "No database query was run for this message.",
            "data_preview": [],
            "used_uploads": False,
            "narrative_kind": kind,
        },
    )


_ALLOWED_CUSTOMER_SCHEMAS = frozenset({"ecommerce", "support"})


def apply_customer_clarification(
    entities: EntityExtractionResult,
    clarification_selection: dict[str, Any] | None,
) -> EntityExtractionResult:    
    if not clarification_selection or not isinstance(
        clarification_selection, dict
    ):
        return entities
    raw_id = clarification_selection.get("id")
    if raw_id is None:
        return entities
    try:
        cid = int(raw_id)
        name = str(clarification_selection.get("name") or "").strip()
        schema = str(clarification_selection.get("schema") or "").strip().lower()
    except (TypeError, ValueError):
        return entities
    if schema not in _ALLOWED_CUSTOMER_SCHEMAS or cid < 1:
        return entities
    display_name = name or entities.customer_name or "Customer"
    email_raw = clarification_selection.get("email")
    email = str(email_raw).strip() if email_raw else ""
    cand: dict[str, object] = {
        "id": cid,
        "name": display_name,
        "schema": schema,
    }
    if email:
        cand["email"] = email
    return replace(
        entities,
        customer_name=name or entities.customer_name,
        customer_candidates=[cand],
        requires_clarification=False,
        spoken_customer_term=entities.spoken_customer_term,
    )


def _customer_id_for_template(
    template_key: str | None,
    entities: EntityExtractionResult,
) -> int | None:

    cands = entities.customer_candidates
    if not cands:
        return None
    if template_key == "open_tickets":
        for c in cands:
            if c.get("schema") == "support":
                return int(c["id"])
        return int(cands[0]["id"])
    for c in cands:
        if c.get("schema") == "ecommerce":
            return int(c["id"])
    return int(cands[0]["id"])


def _entity_sql_hint(entities: EntityExtractionResult) -> str | None:
    if entities.requires_clarification or len(entities.customer_candidates) != 1:
        return None
    c = entities.customer_candidates[0]
    sid = int(c["id"])
    name = str(c["name"]).replace("'", "''")
    schema = str(c["schema"])
    email = str(c.get("email") or "").strip()
    email_line = (
        f", customers.email='{email.replace(chr(39), chr(39)+chr(39))}'"
        if email
        else ""
    )
    return (
        "Resolved customer for this question — you MUST filter using this row only: "
        f"prefer matching `customers.id = {sid}` in schema {schema!r}, OR "
        f"`customers.name = '{name}'` with that exact spelling "
        "(never substitute a shorter first name or nickname).\n"
        f"- schema={schema!r}, customers.id={sid}, customers.name='{name}'{email_line}\n"
        "When joining ecommerce and support for the same person, prefer matching on "
        "`LOWER(TRIM(ecommerce.customers.email)) = LOWER(TRIM(support.customers.email))`.\n"
        "If the user wrote only a first name or nickname, still use this canonical row."
    )


def _template_params(
    template_key: str | None,
    entities: EntityExtractionResult,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    cid = _customer_id_for_template(template_key, entities)
    if cid is not None:
        params["customer_id"] = cid
    if template_key == "customer_orders_recent":
        params["__PG_INTERVAL__"] = interval_sql(entities.time_period)
    return params


class NLQueryPipeline:
    def __init__(self) -> None:
        self._classifier = IntentClassifier()
        self._plan_generator = PlanGenerator()
        self._validator = SQLValidator()
        self._formatter = ResponseFormatter()

    async def run(
        self,
        db: Session,
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
                        return _llm_narrator_failed_response(e)
                    conv_ctx.note_plain_followup_turn(cid_scope)
                    return _plain_followup_response(msg)

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

            has_uploads = conversation_has_uploads(db, cid_scope)

            sem = route_semantic_intent(
                normalized_query, entities, has_uploads=has_uploads
            )

            sql_result: SQLGenerationResult | None = None
            data_narrative_kind: NarrativeKind | None = None

            if sem.intent == SemanticIntent.CUSTOMER_360:
                qp360 = query_plan_customer_360_from_entities(
                    entities, conversation_id=cid_scope
                )
                if qp360 is not None:
                    sql_result = build_sql_from_plan(qp360)
                    data_narrative_kind = "customer_360"
            elif sem.intent == SemanticIntent.SAMPLE_DATA_OVERVIEW:
                sql_result = build_sql_from_plan(
                    QueryPlan(intent=PlanIntent.SAMPLE_DATA_OVERVIEW)
                )
                data_narrative_kind = "sample_data_overview"
            elif sem.intent == SemanticIntent.UPLOAD_DATASET_PREVIEW:
                sql_result = build_sql_from_plan(
                    QueryPlan(
                        intent=PlanIntent.UPLOAD_DATASET_PREVIEW,
                        conversation_id=cid_scope,
                    )
                )
                data_narrative_kind = "upload_dataset_preview"

            if sql_result is None:
                classification = self._classifier.classify(
                    normalized_query,
                    has_customer=bool(entities.customer_candidates),
                    has_time_period=bool(entities.time_period),
                )

                if (
                    classification.use_template
                    and classification.template_key
                    and not has_uploads
                ):
                    tpl = TemplateQueryExecutor()
                    sql_result = tpl.execute(
                        classification.template_key,
                        _template_params(classification.template_key, entities),
                    )
                else:
                    try:
                        payload = await self._plan_generator.generate_async(
                            user_query=normalized_query,
                            entity_context=_combined_sql_context(
                                entities, cid_scope
                            ),
                            has_uploads=has_uploads,
                        )
                    except ValueError as e:
                        err_s = str(e).lower()
                        if (
                            "pollinations_api_key" in err_s
                            or "not set" in err_s
                            or "api key" in err_s
                        ):
                            return ChatResponse(
                                type="error",
                                message=_friendly_error_message(
                                    str(e), "sql_generation"
                                ),
                                suggestions=DEFAULT_SUGGESTIONS,
                            )
                        if "invalid_llm_plan_json" in err_s:
                            return await _llm_clarification_response(
                                user_query,
                                reason_code="invalid_llm_plan_json",
                                detail="planner returned malformed JSON",
                                spoken_name=entities.spoken_customer_term,
                            )
                        raise
                    except Exception as e:
                        logger.warning("llm_plan_generation_failed: %s", e)
                        return ChatResponse(
                            type="error",
                            message=_friendly_error_message(
                                str(e), "sql_generation"
                            ),
                            suggestions=DEFAULT_SUGGESTIONS,
                        )

                    if payload.intent == "not_a_data_question":
                        return await _conversational_chat_response(
                            user_query, cid_scope
                        )

                    base = payload.to_query_plan(conversation_id=cid_scope)

                    if base.intent == PlanIntent.UNSUPPORTED:
                        recovery = build_recovery_suggestions(
                            db, user_query, entities
                        )
                        extra: dict[str, Any] = {"error_kind": "unsupported_plan"}
                        if recovery:
                            extra["follow_up_suggestions"] = recovery
                        return await _llm_clarification_response(
                            user_query,
                            reason_code="unsupported_plan",
                            detail=(
                                "no safe deterministic plan; ask user to narrow "
                                "to orders, tickets, or one specific customer"
                            ),
                            spoken_name=entities.spoken_customer_term,
                            extra_metadata=extra,
                        )

                    if base.intent == PlanIntent.TEMPLATE and base.template_key:
                        if base.template_key not in TemplateQueryExecutor.TEMPLATES:
                            return await _llm_clarification_response(
                                user_query,
                                reason_code="unknown_template",
                                detail=(
                                    f"planner returned unknown template "
                                    f"'{base.template_key}'"
                                ),
                                spoken_name=entities.spoken_customer_term,
                            )
                        tpl = TemplateQueryExecutor()
                        sql_result = tpl.execute(
                            base.template_key,
                            _template_params(base.template_key, entities),
                        )
                    elif base.intent == PlanIntent.CUSTOMER_360:
                        merged = merge_entity_customer_context(base, entities)
                        if not (merged.canonical_customer_name or "").strip() and not (
                            merged.canonical_customer_email or ""
                        ).strip():
                            if query_matches_sample_data_overview(
                                normalized_query
                            ):
                                sql_result = build_sql_from_plan(
                                    QueryPlan(
                                        intent=PlanIntent.SAMPLE_DATA_OVERVIEW
                                    )
                                )
                                data_narrative_kind = "sample_data_overview"
                            else:
                                return await _llm_clarification_response(
                                    user_query,
                                    reason_code="customer_360_no_canonical",
                                    detail=(
                                        "user asked for a full customer overview "
                                        "but no single customer could be resolved "
                                        "from the database"
                                    ),
                                    spoken_name=entities.spoken_customer_term,
                                )
                        else:
                            sql_result = build_sql_from_plan(merged)
                            data_narrative_kind = "customer_360"
                    elif base.intent == PlanIntent.SAMPLE_DATA_OVERVIEW:
                        sql_result = build_sql_from_plan(
                            QueryPlan(intent=PlanIntent.SAMPLE_DATA_OVERVIEW)
                        )
                        data_narrative_kind = "sample_data_overview"
                    elif base.intent == PlanIntent.UPLOAD_DATASET_PREVIEW:
                        if not has_uploads:
                            return await _llm_clarification_response(
                                user_query,
                                reason_code="uploads_required_but_missing",
                                detail=(
                                    "user asked to preview uploaded files but no "
                                    "CSV/Excel has been uploaded in this chat yet"
                                ),
                                spoken_name=entities.spoken_customer_term,
                            )
                        sql_result = build_sql_from_plan(
                            QueryPlan(
                                intent=PlanIntent.UPLOAD_DATASET_PREVIEW,
                                conversation_id=cid_scope,
                            )
                        )
                        data_narrative_kind = "upload_dataset_preview"
                    else:
                        return ChatResponse(
                            type="error",
                            message=_friendly_error_message(
                                None, "sql_generation"
                            ),
                            suggestions=DEFAULT_SUGGESTIONS,
                        )

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
                return _validation_error_response(validation, sql_result.sql)

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
                return _llm_narrator_failed_response(e)

            formatted = self._formatter.format(
                message=narrative_message,
                data=data,
                sql=sql_result.sql,
                strategy=sql_result.strategy.value,
                confidence=sql_result.confidence,
                used_uploads=has_uploads,
            )

            recovery = (
                build_recovery_suggestions(db, user_query, entities)
                if not data
                else []
            )

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
