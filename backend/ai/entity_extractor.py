from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from rapidfuzz import fuzz as _rapidfuzz_fuzz
except ImportError:
    _rapidfuzz_fuzz = None

from ai.interfaces import EntityExtractionResult
from logger import logger

_SPURIOUS_NAME_PARTS = frozenset(
    {
        "orders",
        "order",
        "tickets",
        "ticket",
        "products",
        "product",
        "customers",
        "customer",
        "categories",
        "category",
        "agents",
        "agent",
        "notes",
        "note",
        "data",
        "database",
        "rows",
        "uploads",
        "files",
        "file",
        "each",
        "all",
        "stats",
        "total",
        "count",
        "sum",
        "value",
        "amount",
        "sales",
        "table",
        "tables",
        "schema",
        "schemas",
        "list",
        "type",
        "types",
        "kinds",
        "kind",
        "spreadsheet",
        "sheet",
        "dataset",
        "datasets",
        "purchase",
        "purchases",
        "the",
        "a",
        "an",
    }
)


def _looks_like_person_slug(raw: str) -> bool:
    parts = [p for p in raw.strip().lower().split() if p]
    if not parts or len(raw.strip()) < 2:
        return False
    return all(p not in _SPURIOUS_NAME_PARTS for p in parts)


_BARE_NAME_RE = re.compile(
    r"^\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s*[.?!]?\s*$"
)


def _dedupe_candidates_cross_schema(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(candidates) <= 1:
        return candidates
    merged: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for c in candidates:
        email = (str(c.get("email") or "")).strip().lower()
        name_key = (str(c.get("name") or "")).strip().lower()
        key = email or (f"name:{name_key}" if name_key else "")
        if not key:
            extras.append(c)
            continue
        schema = str(c.get("schema") or "")
        cid = c.get("id")
        if key not in merged:
            entry = dict(c)
            if schema == "ecommerce":
                entry["ecommerce_id"] = cid
            elif schema == "support":
                entry["support_id"] = cid
            merged[key] = entry
            continue
        entry = merged[key]
        if schema == "ecommerce" and entry.get("ecommerce_id") is None:
            entry["ecommerce_id"] = cid
        elif schema == "support" and entry.get("support_id") is None:
            entry["support_id"] = cid
        if entry.get("ecommerce_id") is not None and entry.get("support_id") is not None:
            entry["schema"] = "both"
        if not entry.get("email") and c.get("email"):
            entry["email"] = c["email"]
    return list(merged.values()) + extras


class EntityExtractor:
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract(self, user_query: str) -> EntityExtractionResult:
        
        try:
            query_lower = user_query.lower()

            customer_name, spoken_term, candidates = self._extract_customer(user_query)

            time_period = self._extract_time_period(query_lower)

            keywords = self._extract_keywords(query_lower)

            requires_clarification = len(candidates) > 1

            result = EntityExtractionResult(
                customer_name=customer_name,
                customer_candidates=candidates,
                time_period=time_period,
                keywords=keywords,
                requires_clarification=requires_clarification,
                spoken_customer_term=spoken_term,
            )
            
            return result

        except Exception as e:
            logger.warning("entity_extractor: %s", e)
            return EntityExtractionResult(
                customer_name=None,
                customer_candidates=[],
                time_period=None,
                keywords=[],
                requires_clarification=False,
                spoken_customer_term=None,
                error=str(e),
            )

    def _extract_customer(
        self, query: str
    ) -> tuple[str | None, str | None, list[dict[str, Any]]]:
        patterns = [
            r"\b(?:all|every)\s+(?:data|info|information|records?)\s+"
            r"(?:related|relating)\s+to\s+([A-Za-z][A-Za-z\s]{0,48}?)(?:\s*[.?]|$)",
            r"\beverything\s+about\s+([A-Za-z][A-Za-z\s]{0,48}?)(?:\s*[.?]|$)",
            r"\bfull\s+(?:profile|picture)\s+(?:for|of|about)\s+"
            r"([A-Za-z][A-Za-z\s]{0,48}?)(?:\s*[.?]|$)",
            r"\b(?:tell|give)\s+me\s+all\s+(?:about|for|on)\s+"
            r"([A-Za-z][A-Za-z\s]{0,48}?)(?:\s*[.?]|$)",
            r"\bcomplete\s+(?:history|record|profile)\s+(?:for|of|about)\s+"
            r"([A-Za-z][A-Za-z\s]{0,48}?)(?:\s*[.?]|$)",
            r"\"([A-Za-z\s]+?)\"",
            r"\bname\s+is\s+([a-z][a-z]*(?:\s+[a-z][a-z]*){0,3})\b",
            r"\bthe\s+([a-z][a-z]*)\s+(?:email|e-?mail)\b",
            r"\b(?:data|info|information|details?)\s+of\s+([a-z]+(?:\s+[a-z]+){0,3})\b",
            r"\bfor\s+(?:customer\s+)?([A-Za-z\s]+?)(?:\s+(?:in|with|from|about|at)|$)",
            r"(?:customer|person|user)\s+([A-Za-z\s]+?)(?:\s+|$)",
            r"\b(?:of|for)\s+([a-z]+(?:\s+[a-z]+){0,3})\s*$",
            r"\b(?:show|give|list|fetch|display|tell|find|get|pull|view|see)"
            r"\s+(?:me\s+)?(?:the\s+|all\s+|any\s+)?"
            r"([a-z]+(?:\s+[a-z]+){0,3})"
            r"\s+(?:data|info|information|details?|profile|history|records?|"
            r"orders?|tickets?|purchases?)\b",
        ]

        customer_name: str | None = None
        spoken_term: str | None = None
        for pattern in patterns:
            match = re.search(pattern, query.strip(), flags=re.IGNORECASE)
            if not match:
                continue
            slug = match.group(1).strip()
            if not _looks_like_person_slug(slug):
                continue
            customer_name = slug
            spoken_term = slug.lower()
            break

        if customer_name is None:
            bare = _BARE_NAME_RE.match(query)
            if bare:
                slug = bare.group(1).strip()
                if _looks_like_person_slug(slug):
                    customer_name = slug
                    spoken_term = slug.lower()

        candidates: list[dict[str, Any]] = []
        if customer_name:
            sql = """
            SELECT id, name, email, 'ecommerce' as schema FROM ecommerce.customers
            WHERE name ILIKE :search
            UNION
            SELECT id, name, email, 'support' as schema FROM support.customers
            WHERE name ILIKE :search
            """

            search_term = f"%{customer_name}%"
            result = self.db.execute(text(sql), {"search": search_term})

            seen: set[tuple[int, str, str]] = set()
            for row in result:
                key = (row[0], row[1], row[3])
                if key not in seen:
                    em = row[2] if row[2] is not None else None
                    candidates.append(
                        {
                            "id": row[0],
                            "name": row[1],
                            "email": em,
                            "schema": row[3],
                        }
                    )
                    seen.add(key)

        if customer_name and len(candidates) > 1:
            candidates = _dedupe_candidates_cross_schema(candidates)

        if customer_name and len(candidates) > 1 and spoken_term:
            candidates = self._rerank_customer_candidates(candidates, spoken_term)

        if customer_name and len(candidates) == 1:
            customer_name = str(candidates[0]["name"])

        return customer_name, spoken_term, candidates

    def _rerank_customer_candidates(
        self, candidates: list[dict[str, Any]], spoken_term: str
    ) -> list[dict[str, Any]]:
        rf = _rapidfuzz_fuzz
        if rf is None:
            return candidates
        st = (spoken_term or "").strip().lower()
        if not st:
            return candidates

        def score(row: dict[str, Any]) -> int:
            return int(rf.ratio(st, str(row.get("name", "")).lower()))

        return sorted(candidates, key=score, reverse=True)
    
    def _extract_time_period(self, query: str) -> str | None:
        if re.search(r"\b(last|past)\s+month\b", query) or re.search(
            r"\bin\s+the\s+last\s+month\b", query
        ):
            return "1_months"

        patterns = {
            r"last\s+(\d+)\s+days?": "days",
            r"last\s+(\d+)\s+weeks?": "weeks",
            r"last\s+(\d+)\s+months?": "months",
            r"past\s+(\d+)\s+days?": "days",
            r"in\s+the\s+last\s+(\d+)\s+days?": "days",
            r"in\s+the\s+last\s+(\d+)\s+months?": "months",
        }

        for pattern, unit in patterns.items():
            match = re.search(pattern, query)
            if match:
                value = int(match.group(1))
                return f"{value}_{unit}"

        return None
    
    def _extract_keywords(self, query: str) -> list[str]:
        
        ecommerce_keywords = ['order', 'purchase', 'product', 'category', 'price', 'bought']
        support_keywords = ['ticket', 'support', 'issue', 'problem', 'agent', 'resolve']
        
        keywords = []
        for keyword in ecommerce_keywords + support_keywords:
            if keyword in query:
                keywords.append(keyword)
        
        return list(set(keywords))