
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.interfaces import EntityExtractionResult

_MAX_SUGGESTIONS = 5

_TIME_WINDOW_TRAIL = re.compile(
    r"\s*[,]?\s*\b("
    r"in\s+the\s+last\s+month|in\s+the\s+past\s+month|"
    r"in\s+the\s+last\s+\d+\s+months?|"
    r"last\s+month|past\s+month|"
    r"last\s+\d+\s+days?|past\s+\d+\s+days?|"
    r"in\s+the\s+last\s+\d+\s+days?"
    r")\s*\??\s*$",
    re.IGNORECASE,
)


def _replace_spoken_with_canonical(query: str, spoken: str, canonical: str) -> str:
    spoken = (spoken or "").strip()
    if not spoken:
        return query
    pattern = re.compile(rf"\b{re.escape(spoken)}\b", re.IGNORECASE)
    return pattern.sub(canonical, query, count=1)


def _strip_trailing_time_window(q: str) -> str:
    s = (q or "").strip()
    s = _TIME_WINDOW_TRAIL.sub("", s).strip()
    return s.rstrip(",.")


def _fuzzy_customer_rows(db: Session, term: str, limit: int) -> list[dict[str, Any]]:
    raw = (term or "").strip()
    if len(raw) < 2:
        return []
    t = f"%{raw}%"
    sql = text(
        """
        SELECT id, name, schema FROM (
            SELECT id, name, 'ecommerce'::text AS schema
            FROM ecommerce.customers
            WHERE name ILIKE :t
            UNION
            SELECT id, name, 'support'::text AS schema
            FROM support.customers
            WHERE name ILIKE :t
        ) u
        LIMIT :lim
        """
    )
    rows = db.execute(sql, {"t": t, "lim": limit}).mappings().all()
    out: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for row in rows:
        key = (int(row["id"]), str(row["name"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "schema": str(row["schema"]),
            }
        )
    return out


def build_recovery_suggestions(
    db: Session | None,
    user_query: str,
    entities: EntityExtractionResult,
) -> list[str]:
    """Build short follow-up questions the user can click to re-run."""
    q = (user_query or "").strip()
    if not q:
        return []

    spoken = (entities.spoken_customer_term or "").strip() or None
    cands = entities.customer_candidates
    canonical = (entities.customer_name or "").strip() or None
    out: list[str] = []
    seen_lower: set[str] = set()

    def push(s: str) -> None:
        s = s.strip()
        if not s:
            return
        key = s.lower()
        if key in seen_lower:
            return
        seen_lower.add(key)
        out.append(s)

    if (
        len(cands) == 1
        and spoken
        and canonical
        and spoken.lower() != canonical.lower()
    ):
        push(_replace_spoken_with_canonical(q, spoken, canonical))

    if len(cands) == 1 and entities.time_period and canonical:
        base = (
            _replace_spoken_with_canonical(q, spoken, canonical)
            if spoken and canonical and spoken.lower() != canonical.lower()
            else q
        )
        widened = _strip_trailing_time_window(base)
        if widened.strip() and widened.lower() != q.lower():
            push(widened)

    if len(cands) > 1:
        if spoken:
            for c in cands[:_MAX_SUGGESTIONS]:
                push(_replace_spoken_with_canonical(q, spoken, str(c["name"])))
        else:
            for c in cands[:_MAX_SUGGESTIONS]:
                push(f"{q} — specify customer: {c['name']} ({c['schema']})")

    if not cands and spoken and db is not None:
        try:
            fuzzy = _fuzzy_customer_rows(db, spoken, limit=_MAX_SUGGESTIONS)
        except Exception:
            fuzzy = []
        for row in fuzzy:
            push(_replace_spoken_with_canonical(q, spoken, str(row["name"])))

    return out[:_MAX_SUGGESTIONS]
