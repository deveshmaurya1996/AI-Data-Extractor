from __future__ import annotations

from openai import AsyncOpenAI

from config import settings
from logger import logger

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        base = (settings.POLLINATIONS_BASE_URL or "").rstrip("/")
        _client = AsyncOpenAI(
            api_key=settings.POLLINATIONS_API_KEY,
            base_url=base,
            timeout=float(settings.POLLINATIONS_TIMEOUT),
        )
    return _client


async def complete_text(*, system: str, user: str) -> str:
    """
    Single-turn chat completion. Used for schema-grounded SQL generation.
    """
    key = (settings.POLLINATIONS_API_KEY or "").strip()
    if not key:
        raise ValueError("POLLINATIONS_API_KEY is not set")

    client = _get_client()
    try:
        response = await client.chat.completions.create(
            model=settings.POLLINATIONS_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1024,
            temperature=0.2,
        )
    except Exception as e:
        logger.warning("pollinations_client: chat.completions failed: %s", e)
        raise

    text = response.choices[0].message.content
    if not text or not text.strip():
        raise ValueError("Pollinations returned empty message content")
    return text.strip()
