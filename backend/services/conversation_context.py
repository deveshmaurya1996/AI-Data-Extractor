
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Any

from ai.interfaces import EntityExtractionResult

_MAX_TURNS = 8
_MAX_TURN_LEN = 320
_MAX_SAMPLE_ROWS = 5
_MAX_CELL = 140
_MAX_SQL_SNIP = 700

_states: dict[str, "ConversationState"] = {}


@dataclass
class ConversationState:
    user_turns: deque[str] = field(
        default_factory=lambda: deque(maxlen=_MAX_TURNS)
    )
    last_mode: str = "none" 
    last_user_query: str = ""
    last_row_count: int = 0
    last_topics: list[str] = field(default_factory=list)
    last_data_sample: list[dict[str, Any]] | None = None
    last_sql_trunc: str | None = None
    customer: dict[str, int | str] | None = None


def clear_memory() -> None:
    _states.clear()


def _get(cid: str) -> ConversationState:
    if cid not in _states:
        _states[cid] = ConversationState()
    return _states[cid]


def append_user_turn(conversation_id: str | None, text: str) -> None:
    cid = (conversation_id or "").strip()
    if not cid:
        return
    t = (text or "").strip()
    if not t:
        return
    if len(t) > _MAX_TURN_LEN:
        t = t[: _MAX_TURN_LEN - 1] + "…"
    _get(cid).user_turns.append(t)


def _clip_cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, float, bool)):
        return v
    s = str(v)
    if len(s) > _MAX_CELL:
        return s[: _MAX_CELL - 1] + "…"
    return s


def _sample_rows(data: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if not data:
        return None
    return [
        {k: _clip_cell(v) for k, v in row.items()} for row in data[:_MAX_SAMPLE_ROWS]
    ]


_PRONOUN = re.compile(
    r"\b("
    r"her|his|him|she|he|they|them|their|theirs|"
    r"that\s+customer|this\s+customer|the\s+same\s+customer"
    r")\b",
    re.IGNORECASE,
)

_PLAIN_FOLLOWUP = re.compile(
    r"\b("
    r"explain|summariz(e|ing)|summary|in\s+plain\s+(english|words)|plain\s+text|"
    r"without\s+(a\s+)?table|no\s+table|just\s+text|prose\s+only|"
    r"what\s+does\s+that\s+mean|break\s+it\s+down|"
    r"tell\s+me\s+more\s+about\s+(that|this)|"
    r"put\s+that\s+in\s+words|interpret\s+(that|this)|"
    r"describe\s+(that|this)|why\s+(did|was|is|do)"
    r")\b",
    re.IGNORECASE,
)

_REF_PRIOR = re.compile(
    r"\b("
    r"that|this|those|the\s+above|last\s+(result|results|answer|reply|table|query)|"
    r"what\s+you\s+(said|told|showed|found)"
    r")\b",
    re.IGNORECASE,
)

_TABULAR_FOLLOWUP = re.compile(
    r"\b("
    r"show\s+(it|that|this)\s+as\s+(a\s+)?table|"
    r"(show|display)\s+(me\s+)?(the\s+)?(table|grid|results?)|"
    r"back\s+to\s+(the\s+)?(table|data|numbers)|"
    r"same\s+(thing|query)\s+(but\s+)?(as\s+)?(a\s+)?table"
    r")\b",
    re.IGNORECASE,
)


def note_customer_from_entities(
    conversation_id: str | None, entities: EntityExtractionResult
) -> None:
    cid = (conversation_id or "").strip()
    if not cid or entities.requires_clarification:
        return
    if len(entities.customer_candidates) != 1:
        return
    c = entities.customer_candidates[0]
    _get(cid).customer = {
        "id": int(c["id"]),
        "name": str(c["name"]),
        "schema": str(c["schema"]),
    }


def apply_context_to_entities(
    conversation_id: str | None,
    entities: EntityExtractionResult,
    user_query: str,
) -> EntityExtractionResult:
    if entities.customer_candidates:
        return entities
    cid = (conversation_id or "").strip()
    if not cid:
        return entities
    st = _states.get(cid)
    if not st or not st.customer:
        return entities
    mem = st.customer
    ql = user_query.lower()
    mem_name = str(mem["name"]).lower()
    mem_tokens = {w for w in re.findall(r"[a-z]{2,}", mem_name)}
    noise = {"uk", "us", "ny", "ca", "st", "dr", "mr", "ms"}
    distinctive = {t for t in mem_tokens if t not in noise and len(t) >= 3}
    q_tokens = set(re.findall(r"[a-z]{2,}", ql))
    overlap = distinctive & q_tokens
    if _PRONOUN.search(ql) or overlap:
        return replace(
            entities,
            customer_name=str(mem["name"]),
            customer_candidates=[
                {"id": mem["id"], "name": mem["name"], "schema": mem["schema"]}
            ],
            requires_clarification=False,
            spoken_customer_term=entities.spoken_customer_term,
        )
    return entities


def snapshot_for_plain_followup(
    conversation_id: str | None,
) -> tuple[str, int, list[dict[str, Any]]] | None:
    cid = (conversation_id or "").strip()
    if not cid:
        return None
    st = _states.get(cid)
    if not st or not st.last_data_sample:
        return None
    return (st.last_user_query, st.last_row_count, st.last_data_sample)


def wants_plain_language_followup(
    conversation_id: str | None, user_query: str
) -> bool:
    cid = (conversation_id or "").strip()
    if not cid:
        return False
    st = _states.get(cid)
    if not st or not st.last_data_sample:
        return False
    if st.last_mode not in ("sql_table", "plain_followup"):
        return False
    q = user_query.strip()
    if not q or len(q) > 520:
        return False
    if not _PLAIN_FOLLOWUP.search(q):
        return False
    return bool(_REF_PRIOR.search(q) or len(q) <= 88)


def wants_tabular_rerun_hint(conversation_id: str | None, user_query: str) -> bool:
    cid = (conversation_id or "").strip()
    if not cid:
        return False
    st = _states.get(cid)
    if not st or st.last_mode not in ("conversational", "plain_followup"):
        return False
    return bool(_TABULAR_FOLLOWUP.search(user_query))


def note_conversational_turn(conversation_id: str | None) -> None:
    cid = (conversation_id or "").strip()
    if not cid:
        return
    _get(cid).last_mode = "conversational"


def note_plain_followup_turn(conversation_id: str | None) -> None:
    cid = (conversation_id or "").strip()
    if not cid:
        return
    _get(cid).last_mode = "plain_followup"


def note_sql_success(
    conversation_id: str | None,
    *,
    user_query: str,
    data: list[dict[str, Any]],
    row_count: int,
    sql_safe: str,
    topic_hints: list[str],
) -> None:  
    cid = (conversation_id or "").strip()
    if not cid:
        return
    st = _get(cid)
    st.last_mode = "sql_table"
    st.last_user_query = (user_query or "").strip()[:_MAX_TURN_LEN]
    st.last_row_count = int(row_count)
    st.last_topics = list(topic_hints)[:16]
    st.last_data_sample = _sample_rows(data)
    sql = (sql_safe or "").strip()
    st.last_sql_trunc = sql[:_MAX_SQL_SNIP] + ("…" if len(sql) > _MAX_SQL_SNIP else "")


def transcript_block_for_sql(conversation_id: str | None) -> str | None:
    cid = (conversation_id or "").strip()
    if not cid:
        return None
    st = _states.get(cid)
    if not st:
        return None
    turns = list(st.user_turns)
    if not turns and not st.last_user_query and not st.customer:
        return None
    parts: list[str] = []
    if turns:
        parts.append("Recent user messages in this chat (oldest to newest):")
        for i, line in enumerate(turns[-6:], 1):
            parts.append(f"  {i}. {line}")
    if st.last_mode == "sql_table" and st.last_user_query:
        parts.append(
            f"Last tabular answer in this thread: {st.last_row_count} row(s); "
            f"topics touched: {', '.join(st.last_topics) or 'general'}."
        )
        if st.last_sql_trunc:
            parts.append(f"Last SQL (truncated): {st.last_sql_trunc}")
    if st.customer:
        parts.append(
            f"Resolved person in thread: {st.customer['name']} "
            f"(customers.id={st.customer['id']}, schema={st.customer['schema']})."
        )
    text = "\n".join(parts).strip()
    return text if text else None


def topic_hints_from_entities(
    entities: EntityExtractionResult, user_query: str
) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for k in entities.keywords or []:
        lk = str(k).lower().strip()
        if lk and lk not in seen:
            seen.add(lk)
            hints.append(lk)
    q = user_query.lower()
    for token in (
        "orders",
        "tickets",
        "customers",
        "products",
        "categories",
        "agents",
        "upload",
        "support",
        "ecommerce",
    ):
        if token in q and token not in seen:
            seen.add(token)
            hints.append(token)
    if entities.customer_name:
        cn = str(entities.customer_name).strip()
        if cn and cn.lower() not in seen:
            hints.append(cn[:48])
    return hints[:14]


def remember_customer(
    conversation_id: str | None, entities: EntityExtractionResult
) -> None:
    note_customer_from_entities(conversation_id, entities)


def apply_sticky_customer(
    conversation_id: str | None,
    entities: EntityExtractionResult,
    user_query: str,
) -> EntityExtractionResult:
    return apply_context_to_entities(conversation_id, entities, user_query)
