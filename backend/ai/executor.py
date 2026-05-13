from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import exc, text
from sqlalchemy.orm import Session

from ai.interfaces import ExecutionResult
from logger import logger


def strip_all_null_columns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop result columns where every value is null/NA (removes useless LLM aliases)."""
    if not rows:
        return rows
    df = pd.DataFrame(rows)
    df = df.loc[:, df.notna().any(axis=0)]
    return df.to_dict(orient="records")


class QueryExecutor:
    
    def __init__(self, db: Session):
        self.db = db
    
    def execute(self, sql: str) -> ExecutionResult:
        
        try:
            result = self.db.execute(text(sql))
            
            data = strip_all_null_columns(
                [dict(row._mapping) for row in result.fetchall()]
            )
            
            return ExecutionResult(
                success=True,
                data=data,
                row_count=len(data)
            )
        
        except exc.ProgrammingError as e:
            logger.warning("executor_sql: %s", e)
            return ExecutionResult(
                success=False,
                data=[],
                row_count=0,
                error=str(e),
                error_type="sql_error"
            )
        
        except exc.TimeoutError:
            logger.warning("executor: query timeout")
            return ExecutionResult(
                success=False,
                data=[],
                row_count=0,
                error="Query took too long",
                error_type="timeout"
            )
        
        except Exception as e:
            logger.warning("executor: %s", e)
            return ExecutionResult(
                success=False,
                data=[],
                row_count=0,
                error=str(e),
                error_type="unknown_error"
            )