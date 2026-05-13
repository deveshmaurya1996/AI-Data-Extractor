from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ai.interfaces import EntityExtractionResult


class PlanIntent(str, Enum):

    NOT_A_DATA_QUESTION = "not_a_data_question"
    CUSTOMER_360 = "customer_360"
    SAMPLE_DATA_OVERVIEW = "sample_data_overview"
    UPLOAD_DATASET_PREVIEW = "upload_dataset_preview"
    TEMPLATE = "template"
    UNSUPPORTED = "unsupported"


class QueryPlan(BaseModel):

    intent: PlanIntent
    template_key: str | None = None
    canonical_customer_name: str | None = None
    canonical_customer_email: str | None = Field(default=None)
    ecommerce_customer_id: int | None = None
    support_customer_id: int | None = None
    conversation_id: str | None = Field(
        default=None, description="Trusted server-side uploads scope"
    )

    model_config = {"extra": "forbid"}

    @field_validator("conversation_id")
    @classmethod
    def _sanitize_cid(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().replace("'", "")[:64]
        return s or None


class LlmPlanPayload(BaseModel):

    intent: Literal[
        "not_a_data_question",
        "customer_360",
        "sample_data_overview",
        "upload_dataset_preview",
        "template",
        "unsupported",
    ]
    template_key: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _template_requires_key(self) -> LlmPlanPayload:
        if self.intent == "template" and not (self.template_key or "").strip():
            raise ValueError("template_key is required when intent is template")
        return self

    def to_query_plan(self, *, conversation_id: str | None) -> QueryPlan:
        intent_map = {
            "not_a_data_question": PlanIntent.NOT_A_DATA_QUESTION,
            "customer_360": PlanIntent.CUSTOMER_360,
            "sample_data_overview": PlanIntent.SAMPLE_DATA_OVERVIEW,
            "upload_dataset_preview": PlanIntent.UPLOAD_DATASET_PREVIEW,
            "template": PlanIntent.TEMPLATE,
            "unsupported": PlanIntent.UNSUPPORTED,
        }
        return QueryPlan(
            intent=intent_map[self.intent],
            template_key=(self.template_key or "").strip() or None,
            conversation_id=conversation_id,
        )


def _resolved_schema_ids(c: dict[str, object]) -> tuple[int | None, int | None]:
    """Return ``(ecommerce_id, support_id)`` from a candidate row.

    Cross-schema duplicates of the same person are merged in the entity
    extractor so a single candidate may already carry both ids via
    ``ecommerce_id`` / ``support_id`` extras. When only a single-schema row
    is present, fall back to ``id`` + ``schema``.
    """
    def _to_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, str)):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    schema = str(c.get("schema") or "")
    eid = _to_int(c.get("ecommerce_id"))
    sid = _to_int(c.get("support_id"))
    if eid is None and schema == "ecommerce":
        eid = _to_int(c.get("id"))
    if sid is None and schema == "support":
        sid = _to_int(c.get("id"))
    return eid, sid


def merge_entity_customer_context(
    plan: QueryPlan, entities: EntityExtractionResult
) -> QueryPlan:
    """Attach resolved customer row when exactly one candidate exists."""
    if len(entities.customer_candidates) != 1:
        return plan
    c = entities.customer_candidates[0]
    eid, sid = _resolved_schema_ids(c)
    if eid is None:
        eid = plan.ecommerce_customer_id
    if sid is None:
        sid = plan.support_customer_id
    email = str(c.get("email") or "").strip() or None
    return plan.model_copy(
        update={
            "canonical_customer_name": str(c["name"]),
            "canonical_customer_email": email,
            "ecommerce_customer_id": eid,
            "support_customer_id": sid,
        }
    )


def query_plan_customer_360_from_entities(
    entities: EntityExtractionResult, *, conversation_id: str | None
) -> QueryPlan | None:
    if len(entities.customer_candidates) != 1:
        return None
    c = entities.customer_candidates[0]
    eid, sid = _resolved_schema_ids(c)
    email = str(c.get("email") or "").strip() or None
    return QueryPlan(
        intent=PlanIntent.CUSTOMER_360,
        canonical_customer_name=str(c["name"]),
        canonical_customer_email=email,
        ecommerce_customer_id=eid,
        support_customer_id=sid,
        conversation_id=conversation_id,
    )
