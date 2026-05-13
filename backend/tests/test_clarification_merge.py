"""Customer clarification merge + template id selection."""

from ai.interfaces import EntityExtractionResult
from services.nl_query_pipeline import (
    apply_customer_clarification,
    _customer_id_for_template,
)


def test_apply_clarification_collapses_ambiguous_candidates():
    entities = EntityExtractionResult(
        customer_name="John",
        customer_candidates=[
            {"id": 1, "name": "John A", "schema": "ecommerce"},
            {"id": 2, "name": "John B", "schema": "support"},
        ],
        time_period=None,
        keywords=[],
        requires_clarification=True,
    )
    out = apply_customer_clarification(
        entities,
        {"id": 2, "name": "John B", "schema": "support"},
    )
    assert out.requires_clarification is False
    assert len(out.customer_candidates) == 1
    assert out.customer_candidates[0]["id"] == 2
    assert out.customer_candidates[0]["schema"] == "support"


def test_apply_clarification_invalid_ignored():
    entities = EntityExtractionResult(
        customer_name="X",
        customer_candidates=[{"id": 1, "name": "X", "schema": "ecommerce"}],
        time_period=None,
        keywords=[],
        requires_clarification=False,
    )
    out = apply_customer_clarification(entities, {"id": -1, "name": "Bad", "schema": "ecommerce"})
    assert out == entities
    out2 = apply_customer_clarification(entities, {"id": 1, "name": "Y", "schema": "warehouse"})
    assert out2 == entities


def test_customer_id_for_template_open_tickets_prefers_support():
    entities = EntityExtractionResult(
        customer_name="Jane",
        customer_candidates=[
            {"id": 10, "name": "Jane", "schema": "ecommerce"},
            {"id": 20, "name": "Jane", "schema": "support"},
        ],
        time_period=None,
        keywords=[],
        requires_clarification=False,
    )
    assert _customer_id_for_template("open_tickets", entities) == 20


def test_customer_id_for_template_orders_prefers_ecommerce():
    entities = EntityExtractionResult(
        customer_name="Jane",
        customer_candidates=[
            {"id": 10, "name": "Jane", "schema": "ecommerce"},
            {"id": 20, "name": "Jane", "schema": "support"},
        ],
        time_period=None,
        keywords=[],
        requires_clarification=False,
    )
    assert _customer_id_for_template("customer_orders_all", entities) == 10
