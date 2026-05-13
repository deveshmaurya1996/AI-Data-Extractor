"""Sample data overview semantic / plan intent."""

from __future__ import annotations

from ai.plan_sql_builder import build_sql_from_plan
from ai.query_plan import PlanIntent, QueryPlan

from ._types import SqlPlanningResult


def build_sample_overview_sql() -> SqlPlanningResult:
    out = SqlPlanningResult()
    out.sql_result = build_sql_from_plan(
        QueryPlan(intent=PlanIntent.SAMPLE_DATA_OVERVIEW)
    )
    out.data_narrative_kind = "sample_data_overview"
    return out
