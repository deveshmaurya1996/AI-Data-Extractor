"""
Golden-path checks for the MNGR assignment example queries.

Requires PostgreSQL at DATABASE_URL (see backend/.env.example) and sample CSVs under
backend/sample-data/ (from ai_data_extraction_chatbot_technical_task_sample_data.zip).

Skipped automatically when the database is unreachable so unit-test runs without Docker.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.query_templates import TemplateQueryExecutor


def _pg_session() -> Session | None:
    try:
        from db.engine import SessionLocal, engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return None
    return SessionLocal()


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    sess = _pg_session()
    if sess is None:
        pytest.skip("PostgreSQL not reachable (set DATABASE_URL and start Postgres)")
    from db.engine import init_db
    from db.seed import DataLoader

    init_db()
    DataLoader().load_all(clear_first=True)
    try:
        yield sess
    finally:
        sess.close()


def test_orders_for_hina_recent_window(db_session: Session) -> None:
    """Assignment: orders from customer X in the last month — anchor on sample dates."""
    sql = """
    SELECT o.id, o.order_date, o.total_value
    FROM ecommerce.orders o
    JOIN ecommerce.customers c ON o.customer_id = c.id
    WHERE c.name = 'Hina Patel'
      AND o.order_date >= (SELECT MAX(order_date) FROM ecommerce.orders) - INTERVAL '45 days'
    ORDER BY o.order_date DESC
    """
    rows = db_session.execute(text(sql)).mappings().all()
    assert len(rows) >= 1


def test_open_tickets_for_ben(db_session: Session) -> None:
    """Assignment: open support tickets for customer Y."""
    tpl = TemplateQueryExecutor()
    r = tpl.execute("open_tickets", {"customer_id": 2})
    assert r.success and r.sql
    rows = db_session.execute(text(r.sql)).mappings().all()
    assert len(rows) >= 1
    assert all(str(row["status"]).lower().strip() == "open" for row in rows)


def test_total_order_value_customers_with_tickets_template(db_session: Session) -> None:
    """Assignment: total order value per customer who has opened support tickets."""
    tpl = TemplateQueryExecutor()
    r = tpl.execute("customer_order_value_with_tickets", {})
    assert r.success and r.sql
    assert "LOWER(TRIM(c.email))" in r.sql
    rows = db_session.execute(text(r.sql)).mappings().all()
    assert len(rows) >= 1
    alice = next((x for x in rows if x.get("name") == "Alice Chen"), None)
    assert alice is not None
    assert int(alice["ticket_count"]) >= 1


def test_customers_purchased_never_ticketed_template(db_session: Session) -> None:
    """Assignment: customers who purchased but never raised support tickets (same email)."""
    tpl = TemplateQueryExecutor()
    r = tpl.execute("customers_no_tickets", {})
    assert r.success and r.sql
    assert "NOT EXISTS" in r.sql
    rows = db_session.execute(text(r.sql)).mappings().all()
    assert len(rows) >= 1
    names = {str(row["name"]) for row in rows}
    assert "Kojo Mensah" in names
