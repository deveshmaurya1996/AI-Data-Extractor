from ai.query_templates import TemplateQueryExecutor
from ai.interfaces import QueryStrategy


def test_execute_customer_orders_all_renders_sql():
    ex = TemplateQueryExecutor()
    r = ex.execute("customer_orders_all", {"customer_id": 1})
    assert r.success is True
    assert r.strategy == QueryStrategy.TEMPLATE
    assert "SELECT" in (r.sql or "").upper()
    assert ":customer_id" not in (r.sql or "")
    assert "1" in (r.sql or "")


def test_unknown_template_fails():
    ex = TemplateQueryExecutor()
    r = ex.execute("nonexistent", {})
    assert r.success is False
    assert "not found" in (r.error or "").lower()


def test_customer_orders_recent_substitutes_interval():
    ex = TemplateQueryExecutor()
    r = ex.execute(
        "customer_orders_recent",
        {"customer_id": 2, "__PG_INTERVAL__": "INTERVAL '7 days'"},
    )
    assert r.success is True
    assert "INTERVAL '7 days'" in (r.sql or "")
    assert "2" in (r.sql or "")
