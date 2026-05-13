"""Tests for the LLM-driven narrative generator.

The narrator is the only sanctioned producer of user-facing chat text. These
tests assert kind-based prompt routing, the verbatim pass-through of the LLM
response, and the hard-fail contract on any LLM error or empty reply.
"""

from __future__ import annotations

import json
from typing import Any, Mapping
from unittest.mock import AsyncMock

import pytest

from ai import narrative_generator
from ai.narrative_generator import _CONVERSATIONAL_KINDS, generate_narrative


def _capture_complete_text(monkeypatch: pytest.MonkeyPatch, return_text: str = "LLM reply"):
    mock = AsyncMock(return_value=return_text)
    monkeypatch.setattr(narrative_generator, "complete_text", mock)
    return mock


def _kwargs(mock: AsyncMock) -> Mapping[str, Any]:
    """Return the kwargs of the most recent awaited call, asserting it exists."""
    assert mock.await_args is not None, "complete_text was not awaited"
    return mock.await_args.kwargs


@pytest.mark.asyncio
async def test_greeting_uses_greeting_prompt(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Hi there. Try: list open tickets for Ben.")
    out = await generate_narrative("greeting", user_query="hi")
    assert out == "Hi there. Try: list open tickets for Ben."
    mock.assert_awaited_once()
    kwargs = _kwargs(mock)
    assert "greeted you" in kwargs["system"]
    payload = json.loads(kwargs["user"])
    assert payload == {"kind": "greeting", "user_question": "hi"}


@pytest.mark.asyncio
async def test_thanks_uses_thanks_prompt(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "You're welcome. Anything else?")
    out = await generate_narrative("thanks", user_query="thanks")
    assert "welcome" in out.lower()
    assert "said thanks" in _kwargs(mock)["system"]


@pytest.mark.asyncio
async def test_identity_help_includes_schema_blurb(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "I'm an analytics assistant.")
    await generate_narrative("identity_help", user_query="what can you do")
    system = _kwargs(mock)["system"]
    assert "ecommerce" in system
    assert "support" in system


@pytest.mark.asyncio
async def test_catalog_guidance_warns_about_uneven_schemas(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Whole-DB tours break easily; ask a specific question.")
    await generate_narrative("catalog_guidance", user_query="row counts for each table")
    system = _kwargs(mock)["system"]
    assert "support.agents" in system
    assert "ecommerce.categories" in system


@pytest.mark.asyncio
async def test_tabular_success_includes_sample_rows(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Three orders totalling $420.")
    sample: list[dict[str, Any]] = [
        {"id": 1, "total_value": 100.0},
        {"id": 2, "total_value": 200.0},
        {"id": 3, "total_value": 120.0},
    ]
    out = await generate_narrative(
        "tabular_success",
        user_query="orders for Hina",
        row_count=3,
        sample_rows=sample,
        strategy="template",
        sql="SELECT id, total_value FROM ecommerce.orders LIMIT 3",
        used_uploads=False,
    )
    assert out == "Three orders totalling $420."
    payload = json.loads(_kwargs(mock)["user"])
    assert payload["kind"] == "tabular_success"
    assert payload["row_count"] == 3
    assert payload["sample_rows"] == sample
    assert payload["strategy"] == "template"
    assert payload["used_uploads"] is False
    assert payload["sql_snippet"].startswith("SELECT id, total_value")


@pytest.mark.asyncio
async def test_tabular_caps_sample_to_five_rows(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Many rows; see table.")
    sample = [{"id": i} for i in range(20)]
    await generate_narrative(
        "tabular_success",
        user_query="show everything",
        row_count=20,
        sample_rows=sample,
        strategy="plan_built",
        sql="SELECT 1",
    )
    payload = json.loads(_kwargs(mock)["user"])
    assert len(payload["sample_rows"]) == 5


@pytest.mark.asyncio
async def test_empty_result_payload_has_zero_rows(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "No rows. Try narrowing the date range.")
    out = await generate_narrative(
        "empty_result",
        user_query="orders for Hina last week",
        row_count=0,
        sample_rows=[],
        strategy="template",
        sql="SELECT 1",
    )
    assert "no rows" in out.lower()
    payload = json.loads(_kwargs(mock)["user"])
    assert payload["row_count"] == 0
    assert payload["sample_rows"] == []


@pytest.mark.asyncio
async def test_customer_360_prompt_mentions_cross_domain(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Alice has 3 orders and 1 open ticket.")
    await generate_narrative(
        "customer_360",
        user_query="everything about Alice",
        row_count=4,
        sample_rows=[{"name": "Alice", "kind": "order"}],
        strategy="plan_built",
        sql="SELECT 1",
    )
    system = _kwargs(mock)["system"]
    assert "cross-domain" in system or "customer 360" in system.lower()


@pytest.mark.asyncio
async def test_sample_data_overview_prompt(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "Seeded: 10 customers, 25 orders, 8 tickets.")
    await generate_narrative(
        "sample_data_overview",
        user_query="show me all data",
        row_count=8,
        sample_rows=[{"table": "customers", "n": 10}],
        strategy="plan_built",
        sql="SELECT 1",
    )
    assert "seeded-data overview" in _kwargs(mock)["system"]


@pytest.mark.asyncio
async def test_upload_dataset_preview_prompt(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "File budget.csv has 50 rows.")
    await generate_narrative(
        "upload_dataset_preview",
        user_query="preview the file I uploaded",
        row_count=50,
        sample_rows=[{"file_name": "budget.csv", "row_index": 0}],
        strategy="plan_built",
        sql="SELECT 1",
        used_uploads=True,
    )
    system = _kwargs(mock)["system"]
    assert "uploads" in system.lower()


@pytest.mark.asyncio
async def test_conversational_payload_omits_sql_and_row_count(monkeypatch: pytest.MonkeyPatch):
    """Conversational kinds get a slim payload — no row_count or sql leakage."""
    mock = _capture_complete_text(monkeypatch, "Hello!")
    await generate_narrative(
        "greeting",
        user_query="hi",
        row_count=5,
        sample_rows=[{"x": 1}],
        sql="SELECT 1",
    )
    payload = json.loads(_kwargs(mock)["user"])
    assert "row_count" not in payload
    assert "sample_rows" not in payload
    assert "sql_snippet" not in payload


@pytest.mark.asyncio
async def test_llm_exception_propagates(monkeypatch: pytest.MonkeyPatch):
    mock = AsyncMock(side_effect=RuntimeError("network down"))
    monkeypatch.setattr(narrative_generator, "complete_text", mock)
    with pytest.raises(RuntimeError, match="network down"):
        await generate_narrative("greeting", user_query="hi")


@pytest.mark.asyncio
async def test_empty_llm_response_raises(monkeypatch: pytest.MonkeyPatch):
    mock = AsyncMock(return_value="   ")
    monkeypatch.setattr(narrative_generator, "complete_text", mock)
    with pytest.raises(ValueError, match="empty narrative"):
        await generate_narrative("greeting", user_query="hi")


@pytest.mark.asyncio
async def test_unknown_kind_raises_before_llm_call(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "anything")
    with pytest.raises(ValueError, match="unknown narrative kind"):
        await generate_narrative("not_a_real_kind", user_query="hi")  # type: ignore[arg-type]
    mock.assert_not_awaited()


def test_conversational_kinds_set_is_complete():
    """Catch accidental drift between the Literal type and the runtime set."""
    expected = {
        "greeting",
        "thanks",
        "identity_help",
        "data_inventory",
        "catalog_guidance",
        "generic_conversational",
        "needs_clarification",
    }
    assert _CONVERSATIONAL_KINDS == expected


@pytest.mark.asyncio
async def test_needs_clarification_includes_structured_context(
    monkeypatch: pytest.MonkeyPatch,
):
    mock = _capture_complete_text(
        monkeypatch,
        "Got it — did you want Alice's ecommerce orders or her support tickets?",
    )
    out = await generate_narrative(
        "needs_clarification",
        user_query="show me alice data",
        clarification_context={
            "reason_code": "customer_360_no_canonical",
            "detail": "no single customer resolved",
            "spoken_name": "alice",
            "known_customer_examples": ["Alice Chen", "Ben Okafor", "Hina Patel"],
            "available_schemas": ["ecommerce", "support"],
        },
    )
    assert out  # LLM reply echoed back
    mock.assert_awaited_once()
    kwargs = _kwargs(mock)
    system = kwargs["system"]
    assert "clarifying question" in system.lower()
    payload = json.loads(kwargs["user"])
    assert payload["kind"] == "needs_clarification"
    assert payload["user_question"] == "show me alice data"
    assert payload["reason_code"] == "customer_360_no_canonical"
    assert payload["spoken_name"] == "alice"
    assert "Alice Chen" in payload["known_customer_examples"]
    assert payload["available_schemas"] == ["ecommerce", "support"]


@pytest.mark.asyncio
async def test_needs_clarification_omits_blank_fields(monkeypatch: pytest.MonkeyPatch):
    mock = _capture_complete_text(monkeypatch, "What did you want to see?")
    await generate_narrative(
        "needs_clarification",
        user_query="hmm",
        clarification_context={
            "reason_code": "unsupported_plan",
            "detail": "",
            "spoken_name": None,
            "known_customer_examples": [],
        },
    )
    payload = json.loads(_kwargs(mock)["user"])
    assert "spoken_name" not in payload
    assert "detail" not in payload
    assert "known_customer_examples" not in payload
    assert payload["reason_code"] == "unsupported_plan"


@pytest.mark.asyncio
async def test_needs_clarification_propagates_llm_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    failing = AsyncMock(side_effect=RuntimeError("pollinations_down"))
    monkeypatch.setattr(narrative_generator, "complete_text", failing)
    with pytest.raises(RuntimeError, match="pollinations_down"):
        await generate_narrative(
            "needs_clarification",
            user_query="anything",
            clarification_context={"reason_code": "unsupported_plan"},
        )
