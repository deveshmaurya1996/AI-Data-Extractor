from ai.plan_sql_builder import build_sql_from_plan
from ai.query_plan import PlanIntent, QueryPlan


def test_customer_360_uses_name_equality_not_random_ilike():
    plan = QueryPlan(
        intent=PlanIntent.CUSTOMER_360,
        canonical_customer_name="Alice Chen",
        canonical_customer_email=None,
        conversation_id=None,
    )
    r = build_sql_from_plan(plan)
    assert r.success and r.sql
    assert "ec.name = 'Alice Chen'" in r.sql
    assert "sc.name = 'Alice Chen'" in r.sql
    assert "fata" not in r.sql.lower()


def test_customer_360_prefers_email_when_present():
    plan = QueryPlan(
        intent=PlanIntent.CUSTOMER_360,
        canonical_customer_name="Alice Chen",
        canonical_customer_email="alice.chen@example.com",
        conversation_id=None,
    )
    r = build_sql_from_plan(plan)
    assert r.success and r.sql
    assert "LOWER(TRIM(ec.email)) = LOWER(TRIM('alice.chen@example.com'))" in r.sql
    assert "ec.name = 'Alice Chen'" not in r.sql


def test_upload_preview_sql_scopes_conversation():
    plan = QueryPlan(
        intent=PlanIntent.UPLOAD_DATASET_PREVIEW,
        conversation_id="abc-123",
    )
    r = build_sql_from_plan(plan)
    assert r.success and r.sql
    assert "d.conversation_id = 'abc-123'" in r.sql


def test_sample_data_overview_row_counts():
    plan = QueryPlan(intent=PlanIntent.SAMPLE_DATA_OVERVIEW)
    r = build_sql_from_plan(plan)
    assert r.success and r.sql
    assert "ecommerce.orders" in r.sql
    assert "support.tickets" in r.sql
    assert "COUNT(*)" in r.sql
