from __future__ import annotations

import re

from ai.interfaces import ValidationResult
from config import settings
from logger import logger


def query_policy_lines() -> list[str]:
    """
    Human-readable rules for what SQL the assistant is allowed to run.
    Shown when validation fails so users know what to change or ask instead.
    """
    v = SQLValidator()
    blocked = ", ".join(sorted(v.FORBIDDEN_KEYWORDS))
    return [
        "Only read-only queries: the SQL must contain SELECT or WITH (CTEs).",
        f"These keywords are never allowed: {blocked}.",
        f"At most {v.max_rows} rows are returned; a LIMIT is applied if the query omits one.",
        f"Each query may run at most {v.query_timeout_ms} ms on the database server.",
        "Ask about ecommerce (orders, products, customers, categories) "
        "or support (tickets, agents, customers), or uploaded files in this chat.",
    ]


class SQLValidator:
    """
    Read-only SQL guardrails. Row cap and statement timeout come from
    ``settings.MAX_ROWS_PER_QUERY`` and ``settings.QUERY_TIMEOUT_MS`` unless
    overridden in the constructor (tests).
    """

    ALLOWED_KEYWORDS = {
        "SELECT", "WITH", "AS", "FROM", "WHERE", "JOIN",
        "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR",
        "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET",
        "UNION", "EXCEPT", "INTERSECT", "DISTINCT", "CASE",
        "WHEN", "THEN", "ELSE", "END", "IN", "NOT", "IS", "NULL"
    }
    
    FORBIDDEN_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXECUTE",
        "PRAGMA", "ATTACH", "DETACH"
    }

    _TOKEN_BOUNDARY = r"(?<![A-Za-z0-9_])"
    _TOKEN_BOUNDARY_END = r"(?![A-Za-z0-9_])"
    _INVALID_ID_AS_TIMESTAMP = re.compile(
        r"(?is)\b(?:[A-Za-z_][\w]*\.)?"
        r"(?:id|ticket_id|customer_id|category_id|agent_id|dataset_id|row_index)\s*"
        r"::\s*text\s*::\s*timestamp(?:z)?\b"
    )

    def __init__(
        self,
        *,
        max_rows: int | None = None,
        query_timeout_ms: int | None = None,
    ) -> None:
        self.max_rows = max_rows if max_rows is not None else settings.MAX_ROWS_PER_QUERY
        self.query_timeout_ms = (
            query_timeout_ms
            if query_timeout_ms is not None
            else settings.QUERY_TIMEOUT_MS
        )

    @classmethod
    def _whole_keyword_re(cls, keyword: str) -> re.Pattern[str]:
        return re.compile(
            cls._TOKEN_BOUNDARY + re.escape(keyword) + cls._TOKEN_BOUNDARY_END,
            re.IGNORECASE,
        )

    @classmethod
    def _find_forbidden_keyword(cls, sql: str) -> str | None:
        for kw in sorted(cls.FORBIDDEN_KEYWORDS, key=len, reverse=True):
            if cls._whole_keyword_re(kw).search(sql):
                return kw
        return None

    @classmethod
    def _has_read_keyword(cls, sql: str) -> bool:
        return bool(
            cls._whole_keyword_re("SELECT").search(sql)
            or cls._whole_keyword_re("WITH").search(sql)
        )

    def validate(self, sql: str) -> ValidationResult:
        
        try:
            forbidden = self._find_forbidden_keyword(sql)
            if forbidden:
                return ValidationResult(
                    is_safe=False,
                    sql_safe=None,
                    reason=f"Query contains forbidden keyword: {forbidden}",
                    error=f"Security violation: {forbidden} not allowed",
                )

            if not self._has_read_keyword(sql):
                return ValidationResult(
                    is_safe=False,
                    sql_safe=None,
                    reason="Query must be SELECT or WITH (read-only)",
                    error="Only SELECT queries allowed",
                )

            if self._INVALID_ID_AS_TIMESTAMP.search(sql):
                return ValidationResult(
                    is_safe=False,
                    sql_safe=None,
                    reason="Invalid cast: numeric ids cannot become timestamps",
                    error=(
                        "Do not use patterns like id::text::timestamp or "
                        "customer_id::text::timestamptz — PostgreSQL cannot parse "
                        "id strings as timestamps. Use the real timestamp column "
                        "(e.g. created_at) or NULL::timestamptz when a branch has none."
                    ),
                )
            
            body = sql.strip().rstrip(";")
            if re.search(r"(?is)\blimit\s+\d+\s*$", body):
                capped = body
            else:
                capped = f"{body}\nLIMIT {self.max_rows}"

            sql_safe = (
                f"SET statement_timeout TO {self.query_timeout_ms};\n{capped};"
            ).strip()
            
            return ValidationResult(
                is_safe=True,
                sql_safe=sql_safe,
                reason="Query is safe to execute"
            )
        
        except Exception as e:
            logger.warning("validator: %s", e)
            return ValidationResult(
                is_safe=False,
                sql_safe=None,
                reason="Validation failed",
                error=str(e)
            )