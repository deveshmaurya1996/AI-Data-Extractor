from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ai.interfaces import EntityExtractionResult


class SemanticIntent(str, Enum):

    CUSTOMER_360 = "customer_360"
    SAMPLE_DATA_OVERVIEW = "sample_data_overview"
    UPLOAD_DATASET_PREVIEW = "upload_dataset_preview"


_CUSTOMER_360_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:all|every)\s+(?:data|info|information|records?)\s+"
        r"(?:related|relating)\s+to\b",
        re.IGNORECASE,
    ),
    re.compile(r"\beverything\s+about\b", re.IGNORECASE),
    re.compile(r"\bfull\s+(?:profile|picture)\b", re.IGNORECASE),
    re.compile(r"\bcomplete\s+(?:history|record)\b", re.IGNORECASE),
    re.compile(
        r"\ball\s+(?:the\s+)?(?:data|info|information)\s+(?:for|on|about)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:tell|give)\s+me\s+all\s+(?:about|for|on)\b", re.IGNORECASE),
    re.compile(
        r"\bentire\s+(?:history|record|profile)\s+(?:for|of|about)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bshow\s+me\s+all\s+(?:data|info|information)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:show|give|list|fetch|display|tell|find|get|pull|view|see)"
        r"\s+(?:me\s+)?(?:the\s+|all\s+|any\s+)?"
        r"[\w'.-]+(?:\s+[\w'.-]+){0,4}"
        r"\s+(?:data|info|information|details?|profile|history|records?)\b",
        re.IGNORECASE,
    ),
)

_PUNCT_RE: re.Pattern[str] = re.compile(r"[^\w\s]")


def _query_is_just_customer_name(
    normalized_query: str, customer_name: str | None
) -> bool:
    if not customer_name:
        return False
    q = _PUNCT_RE.sub(" ", normalized_query).strip().lower()
    name = _PUNCT_RE.sub(" ", customer_name).strip().lower()
    if not q or not name:
        return False
    q = " ".join(q.split())
    name = " ".join(name.split())
    return q == name

_SAMPLE_DATA_OVERVIEW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bshow\s+me\s+all\s+(?:data|info|information)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\ball\s+the\s+data\b", re.IGNORECASE),
    re.compile(r"\boverview\s+of\s+(?:the\s+)?(?:sample\s+)?data\b", re.IGNORECASE),
    re.compile(
        r"\bwhat\s+data\s+(?:do\s+you\s+have|is\s+available|exists|can\s+i\s+see)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:browse|explore)\s+(?:the\s+)?(?:sample\s+)?(?:data|database)\b",
        re.IGNORECASE,
    ),
)

_NARROW_ORDER_OR_TICKET: re.Pattern[str] = re.compile(
    r"\b("
    r"open\s+tickets?|pending\s+tickets?|"
    r"orders?\s+(?:from|in|during|for)|"
    r"purchases?\s+(?:from|in|during|for)|"
    r"last\s+month|past\s+month|in\s+the\s+last"
    r")\b",
    re.IGNORECASE,
)

_UPLOAD_PREVIEW_HINT: re.Pattern[str] = re.compile(
    r"\b("
    r"list|show|preview|display|see"
    r")\b.*\b("
    r"upload|uploaded|attachment|attachments|file|files|spreadsheet|csv|excel|my\s+data"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SemanticRoute:
    intent: SemanticIntent | None


def query_matches_sample_data_overview(normalized_query: str) -> bool:
    q = (normalized_query or "").strip()
    if not q:
        return False
    return any(p.search(q) for p in _SAMPLE_DATA_OVERVIEW_PATTERNS)


def route_semantic_intent(
    normalized_query: str,
    entities: EntityExtractionResult,
    *,
    has_uploads: bool,
) -> SemanticRoute:
    q = (normalized_query or "").strip()
    if not q:
        return SemanticRoute(None)

    if len(entities.customer_candidates) == 1 and not _NARROW_ORDER_OR_TICKET.search(q):
        for pat in _CUSTOMER_360_PATTERNS:
            if pat.search(q):
                return SemanticRoute(SemanticIntent.CUSTOMER_360)
        if _query_is_just_customer_name(q, entities.customer_name):
            return SemanticRoute(SemanticIntent.CUSTOMER_360)

    if has_uploads and _UPLOAD_PREVIEW_HINT.search(q):
        return SemanticRoute(SemanticIntent.UPLOAD_DATASET_PREVIEW)

    if len(entities.customer_candidates) != 1:
        for pat in _SAMPLE_DATA_OVERVIEW_PATTERNS:
            if pat.search(q):
                return SemanticRoute(SemanticIntent.SAMPLE_DATA_OVERVIEW)

    return SemanticRoute(None)
