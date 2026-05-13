from __future__ import annotations

import json
from typing import Any

from ai.pollinations_client import complete_text
from logger import logger


async def summarize_last_tabular_answer_async(
    *,
    follow_up_question: str,
    prior_user_question: str,
    row_count: int,
    sample_rows: list[dict[str, Any]],
) -> str:
    """
    Produce a short prose explanation from the last query + a small row sample.
    No SQL; bounded context only.
    """
    payload = {
        "follow_up_question": follow_up_question,
        "prior_user_question": prior_user_question,
        "row_count": row_count,
        "sample_rows": sample_rows,
    }
    user = json.dumps(payload, ensure_ascii=False, default=str)
    system = (
        "The user is asking about their previous data answer in the same chat. "
        "You see only a small sample of rows (the app may have shown more in the UI). "
        "Reply in clear, concise prose (under 140 words). No SQL, no markdown fences. "
        "If the sample is insufficient to answer precisely, say what you can infer and "
        "suggest one concrete follow-up question or point them to the table above."
    )
    try:
        return (await complete_text(system=system, user=user)).strip()
    except Exception as e:
        logger.warning("followup_summarizer: %s", e)
        raise
