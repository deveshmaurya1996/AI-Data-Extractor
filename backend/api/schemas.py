from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Show me all orders for John Smith in the last month",
                "clarification_selection": {
                    "id": 3,
                    "name": "John Smith",
                    "schema": "ecommerce",
                    "email": "john.smith@example.com",
                },
            }
        }
    )

    query: str
    conversation_id: Optional[str] = None
    clarification_selection: Optional[Dict[str, Any]] = None


class ClarificationSuggestion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    data_schema: str = Field(..., alias="schema")
    email: Optional[str] = None


class ChatResponseSuccess(BaseModel):
    type: str = "success"
    message: str
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ChatResponseClarification(BaseModel):
    type: str = "clarification"
    message: str
    suggestions: List[ClarificationSuggestion]
    metadata: Optional[Dict[str, Any]] = None


class ChatResponseError(BaseModel):
    type: str = "error"
    message: str
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


ChatResponseUnion = Union[
    ChatResponseSuccess,
    ChatResponseClarification,
    ChatResponseError,
]
