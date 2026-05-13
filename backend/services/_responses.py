
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ai.interfaces import ChatResponse, ValidationResult
from ai.narrative_generator import NarrativeKind
from ai.validator import query_policy_lines
from logger import logger


def _friendly_error_message(raw: str | None, context: str) -> str:
    """Turn internal/API errors into short user-facing text (full detail stays in logs)."""
    if context == "llm_narrative":
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
    if "insufficient_quota" in lower or ("429" in raw and "quota" in lower):
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


def validation_error_response(
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


def plain_followup_response(message: str) -> ChatResponse:
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


def llm_narrator_failed_response(exc: BaseException) -> ChatResponse:
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


_GenerateFn = Callable[..., Awaitable[str]]


async def llm_clarification_response(
    user_query: str,
    *,
    reason_code: str,
    detail: str,
    spoken_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
    generate_narrative: _GenerateFn,
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
        return llm_narrator_failed_response(e)

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


_ClassifyConvFn = Callable[[str], NarrativeKind]
_NoteConvFn = Callable[[str | None], None]


async def conversational_chat_response(
    user_query: str,
    conversation_id: str | None,
    *,
    generate_narrative: _GenerateFn,
    classify_conversational_kind: _ClassifyConvFn,
    note_conversational_turn: _NoteConvFn,
) -> ChatResponse:
    kind: NarrativeKind = classify_conversational_kind(user_query)
    try:
        message = await generate_narrative(kind, user_query=user_query)
    except Exception as e:
        return llm_narrator_failed_response(e)

    note_conversational_turn(conversation_id)
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


__all__ = [
    "_KNOWN_CUSTOMER_EXAMPLES",
    "DEFAULT_SUGGESTIONS",
    "_friendly_error_message",
    "_truncate_sql_preview",
    "conversational_chat_response",
    "llm_clarification_response",
    "llm_narrator_failed_response",
    "plain_followup_response",
    "validation_error_response",
]
