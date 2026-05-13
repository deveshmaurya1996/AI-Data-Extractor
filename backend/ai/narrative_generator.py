
from __future__ import annotations

import json
from typing import Any, Literal

from ai.pollinations_client import complete_text
from logger import logger

NarrativeKind = Literal[
    "greeting",
    "thanks",
    "identity_help",
    "data_inventory",
    "catalog_guidance",
    "generic_conversational",
    "tabular_success",
    "empty_result",
    "customer_360",
    "sample_data_overview",
    "upload_dataset_preview",
    "needs_clarification",
]

_CONVERSATIONAL_KINDS: frozenset[NarrativeKind] = frozenset(
    {
        "greeting",
        "thanks",
        "identity_help",
        "data_inventory",
        "catalog_guidance",
        "generic_conversational",
        "needs_clarification",
    }
)

_SCHEMA_BLURB = (
    "Two PostgreSQL domains are queryable:\n"
    "- ecommerce: customers, categories, products, orders\n"
    "- support: customers, agents, tickets, ticket_notes\n"
    "The same person can appear in both domains; they are linked by "
    "LOWER(TRIM(email)). Users can also upload CSV/Excel files in a chat "
    "(uploads.datasets, uploads.dataset_rows) and ask questions about those rows."
)

_BASE_PERSONA = (
    "You are the AI Data Extraction assistant — a conversational interface over "
    "the ecommerce and support PostgreSQL schemas. Reply in clean prose, no SQL, "
    "no markdown code fences, no bullet bloat. Keep responses short and concrete."
)

_TABLE_SAMPLES_PROMPT = (
    "You will receive a JSON payload with the user's question, the SQL strategy "
    "that produced the answer (templates, deterministic plan, or LLM plan), the "
    "row count, and up to five sample rows. Summarize the result for the user in "
    "plain English. Reference concrete values from the sample (names, totals, "
    "dates) when row_count <= 5. When row_count > 5, give a one-sentence overview "
    "and point them at the results table for full detail. Never claim to have run "
    "writes — every query is read-only. Stay under 140 words. Never fence SQL or JSON."
)


def _system_prompt(kind: NarrativeKind) -> str:
    if kind == "greeting":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user just greeted you (hi, hello, hey, thanks-style opener) or "
            "asked for help with no specific data question. Reply with one or two "
            "short sentences: a friendly acknowledgement plus one example data "
            "question they could ask next. Mention both ecommerce and support so "
            "they know the scope.\n\n"
            f"{_SCHEMA_BLURB}"
        )
    if kind == "thanks":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user said thanks. Reply with one short, warm sentence and offer "
            "to take another data question across ecommerce or support. No lists."
        )
    if kind == "identity_help":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user is asking what you are or what you can do. Explain in 2–4 "
            "sentences: you translate plain-English questions into read-only SQL "
            "across two domains, then summarize the result. Mention the schemas "
            "by name and that uploads are supported per chat. End by inviting one "
            "concrete question.\n\n"
            f"{_SCHEMA_BLURB}"
        )
    if kind == "data_inventory":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user is asking what data is available. List the two domains "
            "(ecommerce, support) and the tables in each in one short paragraph. "
            "Mention CSV uploads briefly. Suggest one specific follow-up question "
            "they can ask next. Do not invent tables that are not in this schema.\n\n"
            f"{_SCHEMA_BLURB}"
        )
    if kind == "catalog_guidance":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user asked a whole-database tour question (e.g. row counts across "
            "every table, min/max dates everywhere). Explain that those break easily "
            "because not every table has the same columns — for example "
            "support.agents has no created_at and ecommerce.categories has no row "
            "timestamps — and steer them to one specific question (e.g. orders for "
            "a named customer, open tickets for someone). Mention that GET /api/schema "
            "is available for the exact column list per table. Keep it under 110 words.\n\n"
            f"{_SCHEMA_BLURB}"
        )
    if kind == "generic_conversational":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The user sent a short acknowledgement or unclear message that is not a "
            "data question (e.g. 'ok', 'cool', 'sure'). Reply with one short sentence "
            "inviting their next data question across the ecommerce and support "
            "schemas. Do not lecture or list capabilities."
        )
    if kind == "tabular_success":
        return (
            f"{_BASE_PERSONA}\n\n"
            f"{_TABLE_SAMPLES_PROMPT}"
        )
    if kind == "empty_result":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The query ran successfully but returned zero rows. The payload tells "
            "you the user's question and the SQL strategy. In 1–3 sentences, say "
            "no rows matched, propose exactly one refinement (narrower time window, "
            "different status, a customer that is in the sample data, etc.), and "
            "stop. Never claim there is no data overall."
        )
    if kind == "customer_360":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The query is a cross-domain customer 360 view. The payload lists rows "
            "from the user's orders, tickets, and ticket notes. Narrate that one "
            "person's activity in 2–4 sentences: order count and any visible totals, "
            "ticket count with statuses, anything notable in notes. Keep it factual "
            "to the sample provided. End by inviting a follow-up about a specific "
            "order or ticket."
        )
    if kind == "sample_data_overview":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The query returned a seeded-data overview: per-table row counts (and "
            "sometimes min/max dates) across ecommerce and support. Summarize the "
            "shape of the seeded data in 2–4 sentences and suggest one specific "
            "follow-up the user can ask now that they know what is in the database."
        )
    if kind == "upload_dataset_preview":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The query previewed the user's uploaded spreadsheet rows for this "
            "chat (uploads.datasets / uploads.dataset_rows). Describe what is in "
            "the preview in 2–3 sentences (file name(s), row counts, headers if "
            "visible) and invite a follow-up question against those rows."
        )
    if kind == "needs_clarification":
        return (
            f"{_BASE_PERSONA}\n\n"
            "The assistant could not safely answer the user's question and needs a "
            "follow-up. The payload contains:\n"
            "- user_question: what they asked\n"
            "- reason_code: why the assistant cannot proceed yet\n"
            "- detail: short machine context (e.g. 'no canonical customer', "
            "'unsupported plan', 'unknown template', 'uploads missing', 'spoken_name')\n"
            "- spoken_name: the name fragment the user mentioned, if any\n"
            "- known_customer_examples: 2–3 customers that DO exist in the seed "
            "data, when available\n\n"
            "Write a single short paragraph (max 3 sentences) that:\n"
            "1. Acknowledges what the user asked (mention the spoken_name if "
            "present).\n"
            "2. Asks ONE concrete clarifying question that would let you answer "
            "next turn — for example, ask whether they want ecommerce orders or "
            "support tickets, or ask them to confirm a specific customer from "
            "known_customer_examples, or ask them to attach a CSV when one is "
            "required.\n"
            "3. Stays friendly and does NOT lecture. Never say 'cannot run that "
            "query' or 'name one customer'. Never include the phrase 'sample "
            "data' verbatim.\n"
            f"{_SCHEMA_BLURB}"
        )
    raise ValueError(f"unknown narrative kind: {kind}")


def _user_payload(
    kind: NarrativeKind,
    *,
    user_query: str,
    row_count: int | None,
    sample_rows: list[dict[str, Any]] | None,
    strategy: str | None,
    sql: str | None,
    used_uploads: bool,
    clarification_context: dict[str, Any] | None,
) -> str:
    payload: dict[str, Any] = {
        "kind": kind,
        "user_question": (user_query or "").strip(),
    }
    if kind == "needs_clarification" and clarification_context:
        for key in (
            "reason_code",
            "detail",
            "spoken_name",
            "known_customer_examples",
            "available_schemas",
        ):
            if key in clarification_context and clarification_context[key] not in (
                None,
                "",
                [],
            ):
                payload[key] = clarification_context[key]
    if kind in _CONVERSATIONAL_KINDS:
        return json.dumps(payload, ensure_ascii=False, default=str)

    payload["row_count"] = int(row_count or 0)
    if sample_rows is not None:
        payload["sample_rows"] = sample_rows[:5]
    if strategy:
        payload["strategy"] = strategy
    if sql:
        snippet = sql.strip()
        payload["sql_snippet"] = (
            snippet if len(snippet) <= 600 else snippet[:600] + "…"
        )
    payload["used_uploads"] = bool(used_uploads)
    return json.dumps(payload, ensure_ascii=False, default=str)


async def generate_narrative(
    kind: NarrativeKind,
    *,
    user_query: str,
    row_count: int | None = None,
    sample_rows: list[dict[str, Any]] | None = None,
    strategy: str | None = None,
    sql: str | None = None,
    used_uploads: bool = False,
    clarification_context: dict[str, Any] | None = None,
) -> str:
    """Produce the user-facing chat message via the LLM.

    Raises on any LLM error or empty response — the caller is expected to
    convert that into a hard-fail error in the chat UI.
    """
    system = _system_prompt(kind)
    user = _user_payload(
        kind,
        user_query=user_query,
        row_count=row_count,
        sample_rows=sample_rows,
        strategy=strategy,
        sql=sql,
        used_uploads=used_uploads,
        clarification_context=clarification_context,
    )
    try:
        text = await complete_text(system=system, user=user)
    except Exception as e:
        logger.warning("narrative_generator: complete_text failed (%s): %s", kind, e)
        raise

    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("narrative_generator: LLM returned empty narrative")
    return cleaned
