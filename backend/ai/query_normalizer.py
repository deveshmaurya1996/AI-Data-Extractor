from __future__ import annotations

import re
from typing import Final

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

_VOCAB_TARGETS: Final[tuple[str, ...]] = (
    "data",
    "date",
    "order",
    "orders",
    "ticket",
    "tickets",
    "customer",
    "customers",
)

_RELATED_CONTEXT: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"related\s+to|relating\s+to|about|for|regarding|"
    r"all\s+data|everything\s+about|full\s+(?:profile|picture)|"
    r"show\s+me\s+all"
    r")\b",
    re.IGNORECASE,
)


def _context_suggests_data_word(query_lower: str) -> bool:
    return bool(_RELATED_CONTEXT.search(query_lower))


def _curated_typo_fixes(text: str) -> str:
    """High-precision replacements (typo near 'data' semantics)."""
    q = text
    # "fata" → "data" when the sentence is about related/all data (MNGR typo case)
    if _context_suggests_data_word(q.lower()) and re.search(r"\bfata\b", q, re.IGNORECASE):
        q = re.sub(r"\bfata\b", "data", q, flags=re.IGNORECASE)
    return q


def _rapidfuzz_token_fixes(text: str) -> str:
    if fuzz is None:
        return text
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return text
    replacements: dict[str, str] = {}
    for w in words:
        if len(w) < 4 or w.lower() in _VOCAB_TARGETS:
            continue
        best: tuple[str, float] | None = None
        wl = w.lower()
        for target in _VOCAB_TARGETS:
            if len(target) < 4:
                continue
            score = fuzz.ratio(wl, target)
            if score >= 88 and (best is None or score > best[1]):
                best = (target, score)
        if best and best[1] >= 88:
            # Do not "fix" tokens that could be names in isolation; only near data context
            if _context_suggests_data_word(text.lower()) and wl != best[0]:
                replacements[w] = best[0]
    out = text
    for raw, rep in replacements.items():
        out = re.sub(rf"\b{re.escape(raw)}\b", rep, out, flags=re.IGNORECASE)
    return out


def normalize_query_for_extraction(raw: str) -> str:
    """
    Normalize user text before entity extraction / routing.
    Collapses whitespace; applies conservative typo fixes.
    """
    s = " ".join((raw or "").split())
    s = _curated_typo_fixes(s)
    s = _rapidfuzz_token_fixes(s)
    return s
