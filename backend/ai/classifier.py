from __future__ import annotations

import re

from ai.interfaces import ClassificationResult
from logger import logger


def _keyword_hit(query_lower: str, kw: str) -> bool:
    """Avoid substring false positives (e.g. 'no' inside 'never')."""
    if len(kw) <= 3:
        return re.search(rf"\b{re.escape(kw)}\b", query_lower) is not None
    return kw in query_lower


class IntentClassifier:
    INTENT_PATTERNS: dict[str, dict] = {
        "customer_orders_recent": {
            "keywords": ["order", "purchase"],
            "exclude": ["ticket", "support"],
            "requires_customer": True,
            "requires_time": True,
        },
        "customer_orders_all": {
            "keywords": ["order", "purchase"],
            "exclude": ["ticket", "support"],
            "requires_customer": True,
            "requires_time": False,
        },
        "open_tickets": {
            "keywords": ["ticket", "support", "open", "pending"],
            "exclude": [],
            "requires_customer": True,
            "requires_time": False,
        },
        "customer_order_value_with_tickets": {
            "keywords": ["total", "order", "value", "ticket"],
            "require_any": ["ticket", "tickets", "support"],
            "exclude": [],
            "requires_customer": False,
            "requires_time": False,
        },
        "customers_no_tickets": {
            "keywords": ["never", "raised", "without"],
            "require_any": ["ticket", "tickets", "support"],
            "exclude": ["open", "pending"],
            "requires_customer": False,
            "requires_time": False,
        },
    }

    def classify(
        self,
        user_query: str,
        has_customer: bool,
        has_time_period: bool,
    ) -> ClassificationResult:
        try:
            query_lower = user_query.lower()
            best_match: str | None = None
            highest_score = 0

            for intent, pattern in self.INTENT_PATTERNS.items():
                keyword_matches = sum(
                    1 for kw in pattern["keywords"] if _keyword_hit(query_lower, kw)
                )
                if keyword_matches == 0:
                    continue

                need_any = pattern.get("require_any")
                if need_any and not any(
                    _keyword_hit(query_lower, sub) for sub in need_any
                ):
                    continue

                if any(ex in query_lower for ex in pattern.get("exclude", [])):
                    continue

                if pattern["requires_customer"] and not has_customer:
                    continue
                if pattern["requires_time"] and not has_time_period:
                    continue

                if keyword_matches > highest_score:
                    highest_score = keyword_matches
                    best_match = intent

            if best_match:
                return ClassificationResult(
                    intent=best_match,
                    confidence=0.95,
                    template_key=best_match,
                    use_template=True,
                    use_ai=False,
                )
            return ClassificationResult(
                intent=None,
                confidence=0.0,
                template_key=None,
                use_template=False,
                use_ai=True,
            )
        except Exception as e:
            logger.warning("classifier: %s", e)
            return ClassificationResult(
                intent=None,
                confidence=0.0,
                template_key=None,
                use_template=False,
                use_ai=True,
                error=str(e),
            )
