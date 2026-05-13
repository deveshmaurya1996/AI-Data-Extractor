
from __future__ import annotations

import re
from typing import Literal

from ai.interfaces import EntityExtractionResult

_DATA_TOKEN_RE = re.compile(
    r"\b(orders?|purchases?|tickets?|products?|categories?|customers?|agents?|"
    r"support|ecommerce|sales|revenue|totals?|counts?|sums?|averages?|avg\b|pending|"
    r"opens?|closed|uploads?|upload|csv|spreadsheet|datasets?|rows?|values?|spent|"
    r"bought|raised|notes?|interactions?|departments?)\b",
    re.IGNORECASE,
)

_GREETING_ONLY = re.compile(
    r"^\s*(hi|hello|hey|yo|sup|hiya|howdy|good\s+(morning|afternoon|evening)|greetings)\b"
    r"[\s,!.?\-]*$",
    re.IGNORECASE,
)

_THANKS_ONLY = re.compile(
    r"^\s*(thanks?|thank\s+you|thx|ty|cheers|appreciate\s+it)\b[\s,!.?\-]*$",
    re.IGNORECASE,
)

_HELP_ONLY = re.compile(r"^\s*help\s*[!?.]?\s*$", re.IGNORECASE)

_LEADING_GREETING_PREFIX = re.compile(
    r"^\s*(hi|hello|hey|yo|hiya|howdy)\b[,!\s]+(?=\S)",
    re.IGNORECASE,
)

_META = re.compile(
    r"\b("
    r"who\s+are\s+you|what\s+('?s|is)\s+your\s+name|"
    r"what\s+(can|do)\s+you(\s+do)?(\s+for\s+me)?|"
    r"what\s+(things|else|all|exactly|specifically)\s+(can|could)\s+you(\s+do)?(\s+for\s+me)?|"
    r"what\s+(can|could)\s+you\s+help(\s+me)?(\s+with)?|"
    r"how\s+can\s+you\s+help(\s+me)?(\s+with)?|"
    r"what\s+are\s+you|what\s+do\s+you\s+offer|"
    r"what\s+are\s+your\s+(capabilities|features|skills)|"
    r"tell\s+me\s+about\s+(yourself|you)|capabilities|"
    r"how\s+does\s+this\s+work|how\s+do\s+i\s+use|what\s+can\s+i\s+ask"
    r")\b",
    re.IGNORECASE,
)

_DATE_OR_NUMBER = re.compile(
    r"\b\d{4}\b|\d+\s*(day|days|week|weeks|month|months|year|years)\b|"
    r"\b(last|past|next)\s+\d+\b|\$\s*\d+|\d+\.\d+",
    re.IGNORECASE,
)

_DATA_INVENTORY = re.compile(
    r"\b("
    r"how\s+many\s+(types?|kinds?|sources?)\s+of\s+data|"
    r"what\s+(types?|kinds?|sources?)\s+of\s+data|"
    r"what\s+data\s+(do\s+you\s+have|can\s+i\s+(ask|query)|is\s+available)|"
    r"what\s+(schemas?|domains?)\s+(are\s+there|do\s+you\s+have|can\s+i\s+use)|"
    r"(which|what)\s+(datasets?|domains?|schemas?)\s+"
    r"(are\s+(there|available)|do\s+you\s+have|can\s+i\s+ask)"
    r")\b",
    re.IGNORECASE,
)

_PANORAMA_CATALOG = re.compile(
    r"\b("
    r"(each|every|all)\s+(the\s+)?tables?|"
    r"\ball\s+the\s+tables?\b|"
    r"\bfor\s+each\s+table\b|"
    r"\bacross\s+(all\s+)?(tables?|schemas?)\b|"
    r"\b(tables?|schemas?)\s+.*\b(count|counts?|rows?)\b|"
    r"\b(count|counts?|rows?)\s+.*\b(tables?|schemas?)\b|"
    r"(high[\s-]*level|bird'?s[\s-]*eye)\s+.*\b(overview|summary|picture)\b.*\b(data|database|db)\b|"
    r"(overview|summary|snapshot)\s+of\s+(the\s+)?(whole\s+)?(database|db|schemas?|data)\b|"
    r"\b(database|schema)\s+tour\b"
    r")\b",
    re.IGNORECASE,
)

_SOFT_ABOUT_STORED_DATA = re.compile(
    r"\b("
    r"what\s+can\s+you\s+tell\s+me\s+about\s+(the\s+)?(data|database|schemas?|this|here)\b|"
    r"tell\s+me\s+about\s+(the\s+)?(data|database|schemas?|this\s+app|what'?s\s+stored)\b|"
    r"what\s*(?:'|\u2019)?s\s+stored\s+(here|in\s+the\s+database)\b|"
    r"what\s+is\s+stored\s+(here|in\s+the\s+database)\b|"
    r"(just|only)\s+wondering\s+(about\s+)?(the\s+)?(data|database)\b"
    r")\b",
    re.IGNORECASE,
)

_EXPLICIT_TABLE_DRILLDOWN = re.compile(
    r"\b("
    r"show|list|find|display|fetch|pull|give\s+me|export|compare|join"
    r")\b.+\b("
    r"orders?|tickets?|customers?|products?|categories?|agents?|"
    r"ticket[\s_]?notes?|interactions?"
    r")\b",
    re.IGNORECASE,
)

ConversationalKind = Literal[
    "greeting",
    "thanks",
    "identity_help",
    "data_inventory",
    "catalog_guidance",
    "generic_conversational",
]


def _strip_optional_leading_greeting(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    m = _LEADING_GREETING_PREFIX.match(t)
    if not m:
        return t
    rest = t[m.end():].strip()
    return rest if rest else t


def _has_strong_data_signal(text: str, entities: EntityExtractionResult) -> bool:
    q = text.strip()
    if not q:
        return False
    if _DATA_TOKEN_RE.search(q):
        return True
    if _DATE_OR_NUMBER.search(q):
        return True
    if entities.time_period:
        return True
    if entities.customer_candidates and _DATA_TOKEN_RE.search(q):
        return True
    lc = q.lower()
    if entities.customer_candidates and any(
        w in lc for w in ("order", "ticket", "purchase", "show", "list", "find", "open", "total")
    ):
        return True
    return False


def _wants_catalog_prose_not_sql(q: str) -> bool:
    if _EXPLICIT_TABLE_DRILLDOWN.search(q):
        return False
    if _PANORAMA_CATALOG.search(q):
        return True
    if _SOFT_ABOUT_STORED_DATA.search(q) and not _DATA_TOKEN_RE.search(q):
        return True
    return False


def should_respond_conversationally(
    user_query: str,
    entities: EntityExtractionResult,
    conversation_id: str | None = None,
) -> bool:
    """True when the message should skip SQL and go straight to the LLM narrator."""
    raw = user_query.strip()
    if not raw:
        return False
    if conversation_id:
        from services import conversation_context as conv_ctx

        if conv_ctx.wants_tabular_rerun_hint(conversation_id, raw):
            return False
    q = _strip_optional_leading_greeting(raw)
    if not q:
        q = raw
    if _wants_catalog_prose_not_sql(q):
        return True
    if _has_strong_data_signal(raw, entities):
        return False
    if _GREETING_ONLY.match(q) or _THANKS_ONLY.match(q) or _HELP_ONLY.match(q):
        return True
    if _META.search(q) and len(q) < 600:
        return True
    if _DATA_INVENTORY.search(q) and len(q) < 500:
        return True
    lc = q.lower()
    if len(q) < 48 and not any(ch.isdigit() for ch in q):
        if lc in (
            "ok",
            "okay",
            "yes",
            "no",
            "cool",
            "nice",
            "got it",
            "sure",
            "yep",
            "nope",
        ):
            return True
    return False


def classify_conversational_kind(user_query: str) -> ConversationalKind:
    """Return the narrative ``kind`` for a non-data turn.

    Used by the pipeline to pick the right system prompt when calling the LLM
    narrator. This module never produces user-visible prose itself.
    """
    raw = user_query.strip()
    q = _strip_optional_leading_greeting(raw) or raw
    if _THANKS_ONLY.match(q):
        return "thanks"
    if _GREETING_ONLY.match(q) or _HELP_ONLY.match(q):
        return "greeting"
    if _META.search(q):
        return "identity_help"
    if _wants_catalog_prose_not_sql(q):
        return "catalog_guidance"
    if _DATA_INVENTORY.search(q):
        return "data_inventory"
    return "generic_conversational"


def is_not_a_data_question_sql(sql: str | None) -> bool:
    if not sql or not sql.strip():
        return False
    normalized = sql.strip().rstrip(";").strip()
    return normalized.upper() == "NOT_A_DATA_QUESTION"
