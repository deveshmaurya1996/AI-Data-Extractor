from __future__ import annotations

from typing import Any

from ai.interfaces import SQLGenerationResult, QueryStrategy
from logger import logger


class TemplateQueryExecutor:
    """Pre-approved SELECT templates (no user string concatenation into SQL)."""

    TEMPLATES: dict[str, dict[str, Any]] = {
        "customer_orders_recent": {
            "sql": """
            SELECT 
                o.id,
                o.order_date,
                o.total_value,
                c.name as customer_name,
                o.status
            FROM ecommerce.orders o
            JOIN ecommerce.customers c ON o.customer_id = c.id
            WHERE c.id = :customer_id
            AND o.order_date >= CURRENT_DATE - __PG_INTERVAL__
            ORDER BY o.order_date DESC
            LIMIT 100
            """,
            "parameters": ["customer_id"],
            "confidence": 1.0,
        },
        
        "customer_orders_all": {
            "sql": """
            SELECT 
                o.id,
                o.order_date,
                o.total_value,
                c.name as customer_name,
                o.status
            FROM ecommerce.orders o
            JOIN ecommerce.customers c ON o.customer_id = c.id
            WHERE c.id = :customer_id
            ORDER BY o.order_date DESC
            LIMIT 100
            """,
            "parameters": ["customer_id"],
            "confidence": 1.0,
        },
        
        "open_tickets": {
            "sql": """
            SELECT 
                t.id,
                t.title,
                t.status,
                t.priority,
                t.created_at,
                a.name as agent_name
            FROM support.tickets t
            LEFT JOIN support.agents a ON t.assigned_agent_id = a.id
            WHERE t.customer_id = :customer_id
            AND LOWER(TRIM(t.status)) = 'open'
            ORDER BY t.priority DESC, t.created_at DESC
            LIMIT 100
            """,
            "parameters": ["customer_id"],
            "confidence": 1.0,
        },
        
        "customer_order_value_with_tickets": {
            "sql": """
            SELECT 
                c.id,
                c.name,
                COUNT(DISTINCT o.id) as order_count,
                COALESCE(SUM(o.total_value), 0) as total_spent,
                COUNT(DISTINCT t.id) as ticket_count
            FROM ecommerce.customers c
            INNER JOIN support.customers sc
              ON LOWER(TRIM(c.email)) = LOWER(TRIM(sc.email))
            INNER JOIN support.tickets t ON sc.id = t.customer_id
            LEFT JOIN ecommerce.orders o ON c.id = o.customer_id
            GROUP BY c.id, c.name
            ORDER BY COALESCE(SUM(o.total_value), 0) DESC
            LIMIT 100
            """,
            "parameters": [],
            "confidence": 1.0,
        },
        
        "customers_no_tickets": {
            "sql": """
            SELECT 
                c.id,
                c.name,
                c.email,
                c.location,
                COUNT(DISTINCT o.id) as order_count,
                SUM(o.total_value) as total_spent
            FROM ecommerce.customers c
            INNER JOIN ecommerce.orders o ON c.id = o.customer_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM support.customers sc
                INNER JOIN support.tickets t ON t.customer_id = sc.id
                WHERE LOWER(TRIM(sc.email)) = LOWER(TRIM(c.email))
            )
            GROUP BY c.id, c.name, c.email, c.location
            ORDER BY SUM(o.total_value) DESC
            LIMIT 100
            """,
            "parameters": [],
            "confidence": 1.0,
        }
    }
    
    def execute(
        self,
        template_key: str,
        parameters: dict[str, Any]
    ) -> SQLGenerationResult:
        
        try:
            if template_key not in self.TEMPLATES:
                return SQLGenerationResult(
                    success=False,
                    sql=None,
                    strategy=QueryStrategy.ERROR,
                    confidence=0.0,
                    explanation="Template not found",
                    error=f"Template '{template_key}' not found"
                )
            
            template = self.TEMPLATES[template_key]
            sql = template["sql"]

            interval_sql = parameters.get("__PG_INTERVAL__", "INTERVAL '30 days'")
            sql = sql.replace("__PG_INTERVAL__", interval_sql)

            for param in template.get("parameters", []):
                if param not in parameters:
                    continue
                value = parameters[param]
                if param == "customer_id":
                    sql = sql.replace(f":{param}", str(int(value)))
                else:
                    safe = str(value).replace("'", "''")
                    sql = sql.replace(f":{param}", f"'{safe}'")
            
            return SQLGenerationResult(
                success=True,
                sql=sql,
                strategy=QueryStrategy.TEMPLATE,
                confidence=1.0,
                explanation="This response used a pre-validated query template."
            )
        
        except Exception as e:
            logger.warning("template_render_error: %s", e)
            return SQLGenerationResult(
                success=False,
                sql=None,
                strategy=QueryStrategy.ERROR,
                confidence=0.0,
                explanation="Template execution failed",
                error=str(e)
            )