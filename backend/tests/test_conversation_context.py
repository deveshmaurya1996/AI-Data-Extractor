from ai.interfaces import EntityExtractionResult
from services import conversation_context as cc


def _ents(**kwargs) -> EntityExtractionResult:
    return EntityExtractionResult(
        customer_name=kwargs.get("customer_name"),
        customer_candidates=kwargs.get("customer_candidates") or [],
        time_period=kwargs.get("time_period"),
        keywords=kwargs.get("keywords") or [],
        requires_clarification=kwargs.get("requires_clarification", False),
        spoken_customer_term=kwargs.get("spoken_customer_term"),
    )


def test_remember_and_sticky_pronoun():
    cc.clear_memory()
    alice = _ents(
        customer_name="Alice Chen",
        customer_candidates=[
            {"id": 1, "name": "Alice Chen", "schema": "ecommerce"},
        ],
    )
    cc.note_customer_from_entities("conv-1", alice)

    follow = _ents(customer_name=None, customer_candidates=[])
    merged = cc.apply_context_to_entities("conv-1", follow, "What is her total order value?")
    assert len(merged.customer_candidates) == 1
    assert merged.customer_candidates[0]["name"] == "Alice Chen"


def test_sticky_name_token_overlap():
    cc.clear_memory()
    cc.note_customer_from_entities(
        "c2",
        _ents(
            customer_candidates=[
                {"id": 1, "name": "Alice Chen", "schema": "ecommerce"},
            ],
        ),
    )
    merged = cc.apply_context_to_entities(
        "c2",
        _ents(customer_name=None, customer_candidates=[]),
        "total spend for chen please",
    )
    assert merged.customer_candidates[0]["name"] == "Alice Chen"


def test_no_sticky_when_unrelated_query():
    cc.clear_memory()
    cc.note_customer_from_entities(
        "c3",
        _ents(
            customer_candidates=[
                {"id": 2, "name": "Ben Okafor", "schema": "support"},
            ],
        ),
    )
    merged = cc.apply_context_to_entities(
        "c3",
        _ents(customer_name=None, customer_candidates=[]),
        "count all customers",
    )
    assert merged.customer_candidates == []


def test_plain_followup_requires_prior_table():
    cc.clear_memory()
    assert cc.wants_plain_language_followup("x", "explain that in plain english") is False
    cc.note_sql_success(
        "x",
        user_query="show alice orders",
        data=[{"a": 1}],
        row_count=4,
        sql_safe="SELECT 1",
        topic_hints=["orders"],
    )
    assert cc.wants_plain_language_followup("x", "explain that in plain english") is True


def test_transcript_block_includes_turns():
    cc.clear_memory()
    cc.append_user_turn("z", "first question")
    cc.append_user_turn("z", "second question")
    block = cc.transcript_block_for_sql("z")
    assert block is not None
    assert "first question" in block
    assert "second question" in block


def test_topic_hints_from_entities():
    e = _ents(keywords=["order"], customer_name="Alice Chen")
    h = cc.topic_hints_from_entities(e, "any tickets today")
    assert "order" in h
    assert "tickets" in h
