from ai.interfaces import EntityExtractionResult
from ai.query_plan import (
    PlanIntent,
    QueryPlan,
    merge_entity_customer_context,
    query_plan_customer_360_from_entities,
)


def _entities(candidates: list[dict[str, object]]) -> EntityExtractionResult:
    return EntityExtractionResult(
        customer_name="Alice Chen",
        customer_candidates=candidates,
        time_period=None,
        keywords=[],
        requires_clarification=False,
        spoken_customer_term="alice",
    )


def test_merge_single_schema_candidate_sets_one_id():
    plan = QueryPlan(intent=PlanIntent.CUSTOMER_360)
    ents = _entities(
        [
            {
                "id": 1,
                "name": "Alice Chen",
                "email": "alice.chen@example.com",
                "schema": "ecommerce",
            }
        ]
    )
    merged = merge_entity_customer_context(plan, ents)
    assert merged.canonical_customer_name == "Alice Chen"
    assert merged.canonical_customer_email == "alice.chen@example.com"
    assert merged.ecommerce_customer_id == 1
    assert merged.support_customer_id is None


def test_merge_cross_schema_candidate_sets_both_ids():
    plan = QueryPlan(intent=PlanIntent.CUSTOMER_360)
    ents = _entities(
        [
            {
                "id": 1,
                "name": "Alice Chen",
                "email": "alice.chen@example.com",
                "schema": "both",
                "ecommerce_id": 1,
                "support_id": 1,
            }
        ]
    )
    merged = merge_entity_customer_context(plan, ents)
    assert merged.ecommerce_customer_id == 1
    assert merged.support_customer_id == 1


def test_customer_360_from_entities_uses_merged_ids():
    ents = _entities(
        [
            {
                "id": 1,
                "name": "Alice Chen",
                "email": "alice.chen@example.com",
                "schema": "both",
                "ecommerce_id": 1,
                "support_id": 2,
            }
        ]
    )
    plan = query_plan_customer_360_from_entities(ents, conversation_id=None)
    assert plan is not None
    assert plan.intent == PlanIntent.CUSTOMER_360
    assert plan.ecommerce_customer_id == 1
    assert plan.support_customer_id == 2


def test_customer_360_from_entities_returns_none_when_no_candidates():
    ents = _entities([])
    assert query_plan_customer_360_from_entities(ents, conversation_id=None) is None
