
from __future__ import annotations

from dataclasses import replace
from typing import Any

from ai.interfaces import EntityExtractionResult
from ai.pg_interval import interval_sql
from services import conversation_context as conv_ctx

_ALLOWED_CUSTOMER_SCHEMAS = frozenset({"ecommerce", "support"})


def apply_customer_clarification(
    entities: EntityExtractionResult,
    clarification_selection: dict[str, Any] | None,
) -> EntityExtractionResult:
    if not clarification_selection or not isinstance(
        clarification_selection, dict
    ):
        return entities
    raw_id = clarification_selection.get("id")
    if raw_id is None:
        return entities
    try:
        cid = int(raw_id)
        name = str(clarification_selection.get("name") or "").strip()
        schema = str(clarification_selection.get("schema") or "").strip().lower()
    except (TypeError, ValueError):
        return entities
    if schema not in _ALLOWED_CUSTOMER_SCHEMAS or cid < 1:
        return entities
    display_name = name or entities.customer_name or "Customer"
    email_raw = clarification_selection.get("email")
    email = str(email_raw).strip() if email_raw else ""
    cand: dict[str, object] = {
        "id": cid,
        "name": display_name,
        "schema": schema,
    }
    if email:
        cand["email"] = email
    return replace(
        entities,
        customer_name=name or entities.customer_name,
        customer_candidates=[cand],
        requires_clarification=False,
        spoken_customer_term=entities.spoken_customer_term,
    )


def customer_id_for_template(
    template_key: str | None,
    entities: EntityExtractionResult,
) -> int | None:
    cands = entities.customer_candidates
    if not cands:
        return None
    if template_key == "open_tickets":
        for c in cands:
            if c.get("schema") == "support":
                return int(c["id"])
        return int(cands[0]["id"])
    for c in cands:
        if c.get("schema") == "ecommerce":
            return int(c["id"])
    return int(cands[0]["id"])


def entity_sql_hint(entities: EntityExtractionResult) -> str | None:
    if entities.requires_clarification or len(entities.customer_candidates) != 1:
        return None
    c = entities.customer_candidates[0]
    sid = int(c["id"])
    name = str(c["name"]).replace("'", "''")
    schema = str(c["schema"])
    email = str(c.get("email") or "").strip()
    email_line = (
        f", customers.email='{email.replace(chr(39), chr(39)+chr(39))}'"
        if email
        else ""
    )
    return (
        "Resolved customer for this question — you MUST filter using this row only: "
        f"prefer matching `customers.id = {sid}` in schema {schema!r}, OR "
        f"`customers.name = '{name}'` with that exact spelling "
        "(never substitute a shorter first name or nickname).\n"
        f"- schema={schema!r}, customers.id={sid}, customers.name='{name}'{email_line}\n"
        "When joining ecommerce and support for the same person, prefer matching on "
        "`LOWER(TRIM(ecommerce.customers.email)) = LOWER(TRIM(support.customers.email))`.\n"
        "If the user wrote only a first name or nickname, still use this canonical row."
    )


def template_params(
    template_key: str | None,
    entities: EntityExtractionResult,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    cid = customer_id_for_template(template_key, entities)
    if cid is not None:
        params["customer_id"] = cid
    if template_key == "customer_orders_recent":
        params["__PG_INTERVAL__"] = interval_sql(entities.time_period)
    return params


def combined_sql_context(
    entities: EntityExtractionResult, conversation_id: str | None
) -> str | None:
    chunks: list[str] = []
    tx = conv_ctx.transcript_block_for_sql(conversation_id)
    if tx:
        chunks.append("Conversation thread context:\n" + tx)
    ent = entity_sql_hint(entities)
    if ent:
        chunks.append(ent)
    if not chunks:
        return None
    return "\n\n".join(chunks)
