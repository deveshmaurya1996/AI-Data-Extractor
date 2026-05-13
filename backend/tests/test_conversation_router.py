

import pytest

from ai.conversation_router import (
    classify_conversational_kind,
    is_not_a_data_question_sql,
    should_respond_conversationally,
)
from ai.interfaces import EntityExtractionResult

_EMPTY = EntityExtractionResult(
    customer_name=None,
    customer_candidates=[],
    time_period=None,
    keywords=[],
    requires_clarification=False,
    spoken_customer_term=None,
)


def _entities(
    *,
    customer_name=None,
    customer_candidates=None,
    time_period=None,
    keywords=None,
    requires_clarification=False,
) -> EntityExtractionResult:
    return EntityExtractionResult(
        customer_name=customer_name,
        customer_candidates=customer_candidates or [],
        time_period=time_period,
        keywords=keywords or [],
        requires_clarification=requires_clarification,
        spoken_customer_term=None,
    )


@pytest.mark.parametrize(
    "text",
    [
        "hi",
        "Hello!",
        "thanks",
        "Thank you.",
        "help",
        "who are you",
        "what can you do",
        "hey what things can you do for me?",
        "Hi, what can you help me with?",
        "how can you help",
        "what are your capabilities",
        "ok",
    ],
)
def test_greetings_and_meta_are_conversational(text: str):
    assert should_respond_conversationally(text, _EMPTY) is True


ASSESSMENT_EXAMPLE_QUERIES = [
    "Show me all orders from customer Hina Patel in the last month",
    "List all open support tickets for customer Ben Okafor",
    "What is the total order value for each customer who has opened support tickets?",
    "Find customers who have made purchases but never raised support tickets",
]


@pytest.mark.parametrize("q", ASSESSMENT_EXAMPLE_QUERIES)
def test_assessment_examples_stay_on_data_path(q: str):
    assert should_respond_conversationally(q, _EMPTY) is False


@pytest.mark.parametrize(
    "q",
    [
        "How many types of data do you have?",
        "what kinds of data are there",
        "What data can I ask about?",
        "which schemas do you have",
    ],
)
def test_data_inventory_questions_are_conversational(q: str):
    assert should_respond_conversationally(q, _EMPTY) is True
    assert classify_conversational_kind(q) == "data_inventory"


@pytest.mark.parametrize(
    "q",
    [
        "Row counts for each table please",
        "Give me a high-level overview of the database",
        "Tell me about the data",
        "What's stored in the database?",
    ],
)
def test_whole_database_catalog_routes_to_conversational(q: str):
    assert should_respond_conversationally(q, _EMPTY) is True
    assert classify_conversational_kind(q) == "catalog_guidance"


def test_explicit_show_orders_stays_on_data_path():
    assert should_respond_conversationally("Show me all orders for Alice", _EMPTY) is False


def test_customer_plus_orders_is_data_not_smalltalk():
    ents = _entities(
        customer_name="Alice",
        customer_candidates=[{"id": 1, "name": "Alice", "schema": "ecommerce"}],
    )
    assert should_respond_conversationally("orders for her", ents) is False


def test_not_a_data_question_sentinel():
    assert is_not_a_data_question_sql("NOT_A_DATA_QUESTION") is True
    assert is_not_a_data_question_sql("not_a_data_question;") is True
    assert is_not_a_data_question_sql("SELECT 1") is False


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hi", "greeting"),
        ("hello!", "greeting"),
        ("help", "greeting"),
        ("thanks", "thanks"),
        ("thank you", "thanks"),
        ("who are you", "identity_help"),
        ("what can you do", "identity_help"),
        ("how many types of data do you have", "data_inventory"),
        ("row counts for each table", "catalog_guidance"),
        ("ok", "generic_conversational"),
        ("sure", "generic_conversational"),
    ],
)
def test_classify_conversational_kind(text: str, expected: str):
    assert classify_conversational_kind(text) == expected
