
from __future__ import annotations

from dataclasses import dataclass

from ai.interfaces import ChatResponse, SQLGenerationResult
from ai.narrative_generator import NarrativeKind


@dataclass
class SqlPlanningResult:
    """Either an early ChatResponse or a SQL draft + narrative hint."""

    chat_response: ChatResponse | None = None
    sql_result: SQLGenerationResult | None = None
    data_narrative_kind: NarrativeKind | None = None
