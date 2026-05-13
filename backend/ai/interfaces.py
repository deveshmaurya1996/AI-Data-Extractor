from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

class QueryStrategy(str, Enum):
    TEMPLATE = "template"
    PLAN_BUILT = "plan_built"
    AI_FALLBACK = "ai_fallback"
    ERROR = "error"

@dataclass
class EntityExtractionResult:
    customer_name: Optional[str]
    customer_candidates: List[Dict[str, Any]]
    time_period: Optional[str]
    keywords: List[str]
    requires_clarification: bool
    spoken_customer_term: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ClassificationResult:
    intent: Optional[str]
    confidence: float
    template_key: Optional[str]
    use_template: bool
    use_ai: bool
    error: Optional[str] = None

@dataclass
class SQLGenerationResult:
    success: bool
    sql: Optional[str]
    strategy: QueryStrategy
    confidence: float
    explanation: str
    error: Optional[str] = None

@dataclass
class ValidationResult:
    is_safe: bool
    sql_safe: Optional[str]
    reason: str
    error: Optional[str] = None

@dataclass
class ExecutionResult:
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    error: Optional[str] = None
    error_type: Optional[str] = None

@dataclass
class FormattedResponse:
    message: str
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class ChatResponse:
    type: str
    message: str
    data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    suggestions: Optional[Union[List[str], List[Dict[str, Any]]]] = None