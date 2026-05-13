
from __future__ import annotations

from ai.interfaces import ClassificationResult, EntityExtractionResult
from ai.query_templates import TemplateQueryExecutor
from services._pipeline_helpers import template_params

from ._types import SqlPlanningResult


def try_classifier_sql(
    classification: ClassificationResult,
    entities: EntityExtractionResult,
    has_uploads: bool,
) -> SqlPlanningResult | None:
    """Keyword classifier → template executor (no uploads). Otherwise continue planning."""
    if (
        classification.use_template
        and classification.template_key
        and not has_uploads
    ):
        tpl = TemplateQueryExecutor()
        out = SqlPlanningResult()
        out.sql_result = tpl.execute(
            classification.template_key,
            template_params(classification.template_key, entities),
        )
        return out
    return None


def sql_from_registered_template(
    template_key: str,
    entities: EntityExtractionResult,
) -> SqlPlanningResult:
    tpl = TemplateQueryExecutor()
    out = SqlPlanningResult()
    out.sql_result = tpl.execute(template_key, template_params(template_key, entities))
    return out
