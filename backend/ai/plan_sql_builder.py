from __future__ import annotations

from ai.interfaces import SQLGenerationResult, QueryStrategy
from ai.query_plan import PlanIntent, QueryPlan
from logger import logger


def _escape_literal(name: str) -> str:
    return (name or "").replace("'", "''")


def build_sql_from_plan(plan: QueryPlan) -> SQLGenerationResult:
    try:
        if plan.intent == PlanIntent.NOT_A_DATA_QUESTION:
            return SQLGenerationResult(
                success=True,
                sql="NOT_A_DATA_QUESTION",
                strategy=QueryStrategy.PLAN_BUILT,
                confidence=1.0,
                explanation="Planner marked non-data.",
            )

        if plan.intent == PlanIntent.UNSUPPORTED:
            return SQLGenerationResult(
                success=False,
                sql=None,
                strategy=QueryStrategy.ERROR,
                confidence=0.0,
                explanation="Unsupported plan intent",
                error="unsupported_intent",
            )

        if plan.intent == PlanIntent.SAMPLE_DATA_OVERVIEW:
            sql = """
SELECT * FROM (
  SELECT 'ecommerce.customers'::text AS dataset, COUNT(*)::bigint AS row_count
  FROM ecommerce.customers
  UNION ALL
  SELECT 'ecommerce.orders', COUNT(*)::bigint FROM ecommerce.orders
  UNION ALL
  SELECT 'ecommerce.products', COUNT(*)::bigint FROM ecommerce.products
  UNION ALL
  SELECT 'ecommerce.categories', COUNT(*)::bigint FROM ecommerce.categories
  UNION ALL
  SELECT 'support.customers', COUNT(*)::bigint FROM support.customers
  UNION ALL
  SELECT 'support.tickets', COUNT(*)::bigint FROM support.tickets
  UNION ALL
  SELECT 'support.ticket_notes', COUNT(*)::bigint FROM support.ticket_notes
  UNION ALL
  SELECT 'support.agents', COUNT(*)::bigint FROM support.agents
) AS sample_counts
ORDER BY dataset
LIMIT 100
""".strip()
            return SQLGenerationResult(
                success=True,
                sql=sql,
                strategy=QueryStrategy.PLAN_BUILT,
                confidence=1.0,
                explanation=(
                    "Deterministic row counts for each seeded ecommerce and support table."
                ),
            )

        if plan.intent == PlanIntent.UPLOAD_DATASET_PREVIEW:
            cid = (plan.conversation_id or "").strip().replace("'", "")[:64]
            if not cid:
                return SQLGenerationResult(
                    success=False,
                    sql=None,
                    strategy=QueryStrategy.ERROR,
                    confidence=0.0,
                    explanation="Missing conversation scope for uploads",
                    error="missing_conversation_id",
                )
            sql = f"""
SELECT
  d.file_name,
  dr.row_index,
  dr.data
FROM uploads.dataset_rows dr
INNER JOIN uploads.datasets d
  ON d.id = dr.dataset_id AND d.conversation_id = '{cid}'
ORDER BY d.file_name, dr.row_index
LIMIT 100
""".strip()
            return SQLGenerationResult(
                success=True,
                sql=sql,
                strategy=QueryStrategy.PLAN_BUILT,
                confidence=1.0,
                explanation="Deterministic upload listing for this conversation.",
            )

        if plan.intent == PlanIntent.CUSTOMER_360:
            name = (plan.canonical_customer_name or "").strip()
            email = (plan.canonical_customer_email or "").strip()
            if not name and not email:
                return SQLGenerationResult(
                    success=False,
                    sql=None,
                    strategy=QueryStrategy.ERROR,
                    confidence=0.0,
                    explanation="customer_360 requires a resolved customer name or email",
                    error="missing_customer_identity",
                )
            if email:
                esc_e = _escape_literal(email)
                sql = f"""
SELECT * FROM (
  SELECT
    'ecommerce_order'::text AS source,
    o.id::text AS ref_id,
    ec.name::text AS person,
    COALESCE(o.order_date::text, o.created_at::text) AS occurred_at,
    o.total_value::text AS detail,
    o.status::text AS extra
  FROM ecommerce.orders o
  JOIN ecommerce.customers ec ON ec.id = o.customer_id
  WHERE LOWER(TRIM(ec.email)) = LOWER(TRIM('{esc_e}'))
  UNION ALL
  SELECT
    'support_ticket'::text,
    t.id::text,
    sc.name::text,
    COALESCE(t.updated_at::text, t.created_at::text),
    t.title::text,
    t.status::text
  FROM support.tickets t
  JOIN support.customers sc ON sc.id = t.customer_id
  WHERE LOWER(TRIM(sc.email)) = LOWER(TRIM('{esc_e}'))
  UNION ALL
  SELECT
    'ticket_note'::text,
    tn.id::text,
    sc2.name::text,
    tn.created_at::text,
    LEFT(tn.note, 500)::text,
    t2.title::text
  FROM support.ticket_notes tn
  JOIN support.tickets t2 ON t2.id = tn.ticket_id
  JOIN support.customers sc2 ON sc2.id = t2.customer_id
  WHERE LOWER(TRIM(sc2.email)) = LOWER(TRIM('{esc_e}'))
) AS customer_360
ORDER BY occurred_at DESC NULLS LAST
LIMIT 100
""".strip()
            else:
                esc = _escape_literal(name)
                sql = f"""
SELECT * FROM (
  SELECT
    'ecommerce_order'::text AS source,
    o.id::text AS ref_id,
    ec.name::text AS person,
    COALESCE(o.order_date::text, o.created_at::text) AS occurred_at,
    o.total_value::text AS detail,
    o.status::text AS extra
  FROM ecommerce.orders o
  JOIN ecommerce.customers ec ON ec.id = o.customer_id
  WHERE ec.name = '{esc}'
  UNION ALL
  SELECT
    'support_ticket'::text,
    t.id::text,
    sc.name::text,
    COALESCE(t.updated_at::text, t.created_at::text),
    t.title::text,
    t.status::text
  FROM support.tickets t
  JOIN support.customers sc ON sc.id = t.customer_id
  WHERE sc.name = '{esc}'
  UNION ALL
  SELECT
    'ticket_note'::text,
    tn.id::text,
    sc2.name::text,
    tn.created_at::text,
    LEFT(tn.note, 500)::text,
    t2.title::text
  FROM support.ticket_notes tn
  JOIN support.tickets t2 ON t2.id = tn.ticket_id
  JOIN support.customers sc2 ON sc2.id = t2.customer_id
  WHERE sc2.name = '{esc}'
) AS customer_360
ORDER BY occurred_at DESC NULLS LAST
LIMIT 100
""".strip()
            return SQLGenerationResult(
                success=True,
                sql=sql,
                strategy=QueryStrategy.PLAN_BUILT,
                confidence=1.0,
                explanation=(
                    "Deterministic cross-domain snapshot for one customer "
                    "(matched by email when available, else by exact name)."
                ),
            )

        return SQLGenerationResult(
            success=False,
            sql=None,
            strategy=QueryStrategy.ERROR,
            confidence=0.0,
            explanation="Plan intent has no SQL builder branch",
            error=f"no_builder_for_{plan.intent.value}",
        )
    except Exception as e:
        logger.warning("plan_sql_builder: %s", e)
        return SQLGenerationResult(
            success=False,
            sql=None,
            strategy=QueryStrategy.ERROR,
            confidence=0.0,
            explanation="Plan SQL build failed",
            error=str(e),
        )
