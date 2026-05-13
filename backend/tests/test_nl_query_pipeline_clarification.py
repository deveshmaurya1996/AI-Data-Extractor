"""Tests for the LLM-driven clarification helper in the NL query pipeline.

The chatbot must never emit canned error prose. When the deterministic
pipeline cannot answer (no canonical customer, unsupported plan, uploads
missing, etc.) we instead ask the LLM to write a context-aware clarifying
question. These tests pin that contract.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from services import nl_query_pipeline


@pytest.mark.asyncio
async def test_clarification_response_uses_llm_with_structured_context(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    async def fake_generate_narrative(kind: str, **kwargs: object) -> str:
        captured["kind"] = kind
        captured.update(kwargs)
        return "Did you mean Alice's ecommerce orders or her support tickets?"

    monkeypatch.setattr(
        nl_query_pipeline,
        "generate_narrative",
        fake_generate_narrative,
    )

    resp = await nl_query_pipeline._llm_clarification_response(
        "show me alice data",
        reason_code="customer_360_no_canonical",
        detail="no single customer resolved",
        spoken_name="alice",
    )

    assert resp.type == "clarification"
    assert resp.message == "Did you mean Alice's ecommerce orders or her support tickets?"
    assert captured["kind"] == "needs_clarification"
    assert captured["user_query"] == "show me alice data"
    ctx = captured["clarification_context"]
    assert isinstance(ctx, dict)
    assert ctx["reason_code"] == "customer_360_no_canonical"
    assert ctx["spoken_name"] == "alice"
    assert "Alice Chen" in ctx["known_customer_examples"]
    assert ctx["available_schemas"] == ["ecommerce", "support"]
    assert resp.metadata is not None
    assert resp.metadata["response_mode"] == "clarification"
    assert resp.metadata["narrative_kind"] == "needs_clarification"
    assert resp.metadata["clarification_reason"] == "customer_360_no_canonical"


@pytest.mark.asyncio
async def test_clarification_response_omits_spoken_name_when_absent(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_ctx: dict[str, object] = {}

    async def fake_generate_narrative(kind: str, **kwargs: object) -> str:
        ctx = kwargs.get("clarification_context")
        if isinstance(ctx, dict):
            captured_ctx.update(ctx)
        return "What did you want to look at?"

    monkeypatch.setattr(
        nl_query_pipeline,
        "generate_narrative",
        fake_generate_narrative,
    )

    resp = await nl_query_pipeline._llm_clarification_response(
        "huh?",
        reason_code="unsupported_plan",
        detail="no safe plan available",
        spoken_name=None,
    )

    assert "spoken_name" not in captured_ctx
    assert captured_ctx["reason_code"] == "unsupported_plan"
    assert resp.type == "clarification"


@pytest.mark.asyncio
async def test_clarification_response_includes_extra_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_generate_narrative(_kind: str, **_kwargs: object) -> str:
        return "Try narrowing to one customer."

    monkeypatch.setattr(
        nl_query_pipeline,
        "generate_narrative",
        fake_generate_narrative,
    )

    resp = await nl_query_pipeline._llm_clarification_response(
        "show me everything",
        reason_code="unsupported_plan",
        detail="too broad",
        extra_metadata={
            "error_kind": "unsupported_plan",
            "follow_up_suggestions": ["Try Hina's orders", "Open tickets for Ben"],
        },
    )

    assert resp.metadata is not None
    assert resp.metadata["error_kind"] == "unsupported_plan"
    assert resp.metadata["follow_up_suggestions"] == [
        "Try Hina's orders",
        "Open tickets for Ben",
    ]
    assert resp.metadata["clarification_reason"] == "unsupported_plan"


@pytest.mark.asyncio
async def test_clarification_response_hard_fails_when_llm_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    failing = AsyncMock(side_effect=RuntimeError("pollinations_down"))
    monkeypatch.setattr(nl_query_pipeline, "generate_narrative", failing)

    resp = await nl_query_pipeline._llm_clarification_response(
        "anything",
        reason_code="unsupported_plan",
        detail="no plan",
    )

    assert resp.type == "error"
    assert resp.metadata is not None
    assert resp.metadata["error_kind"] == "llm_narrator_unavailable"
    # Friendly hard-fail string is non-empty and mentions the AI service.
    assert resp.message
    assert "AI service" in resp.message or "Pollinations" in resp.message


@pytest.mark.asyncio
async def test_known_customer_examples_match_seed_data():
    """Pin the seed customers we hint to the LLM — drift here would mislead users."""
    assert nl_query_pipeline._KNOWN_CUSTOMER_EXAMPLES == (
        "Alice Chen",
        "Ben Okafor",
        "Hina Patel",
    )


def test_clarification_payload_is_json_serializable():
    """The pipeline serializes context to JSON before sending to the LLM —
    confirm every field is plain-typed."""
    payload = {
        "reason_code": "customer_360_no_canonical",
        "detail": "no canonical customer",
        "available_schemas": ["ecommerce", "support"],
        "known_customer_examples": list(nl_query_pipeline._KNOWN_CUSTOMER_EXAMPLES),
        "spoken_name": "alice",
    }
    serialized = json.dumps(payload)
    assert "Alice Chen" in serialized
    assert "ecommerce" in serialized
