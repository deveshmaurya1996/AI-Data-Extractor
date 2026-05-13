from __future__ import annotations

import json

from pydantic import ValidationError

from ai.pollinations_client import complete_text
from ai.prompts import PLAN_GENERATION_SYSTEM, PLAN_GENERATION_USER_PREFIX
from ai.query_plan import LlmPlanPayload
from logger import logger


def _extract_json_object(raw: str) -> dict[str, object]:
    s = (raw or "").strip()
    if "```" in s:
        if "```json" in s.lower():
            idx = s.lower().index("```json")
            s = s[idx + 7 :].split("```", 1)[0].strip()
        else:
            s = s.split("```", 1)[1].split("```", 1)[0].strip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no_json_object")
    return json.loads(s[start : end + 1])


class PlanGenerator:

    async def generate_async(
        self,
        *,
        user_query: str,
        entity_context: str | None,
        has_uploads: bool,
    ) -> LlmPlanPayload:
        hints: list[str] = []
        if has_uploads:
            hints.append(
                "This chat has uploaded spreadsheet rows in schema uploads "
                "(datasets + dataset_rows)."
            )
        block = "\n".join(hints)
        if entity_context and entity_context.strip():
            block = (block + "\n\n" if block else "") + entity_context.strip()

        user_body = (
            f"{PLAN_GENERATION_USER_PREFIX.strip()}\n\n"
            f"{block}\n\n"
            f"User message:\n{user_query.strip()}\n"
        )
        raw = await complete_text(
            system=PLAN_GENERATION_SYSTEM.strip(),
            user=user_body,
        )
        try:
            data = _extract_json_object(raw)
            return LlmPlanPayload.model_validate(data)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.warning("plan_generator_parse: %s raw=%r", e, raw[:400])
            raise ValueError("invalid_llm_plan_json") from e
