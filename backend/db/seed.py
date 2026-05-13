
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import text

from db.engine import Base, SessionLocal, engine
from logger import logger

# CSV columns allowed per table (must match ORM columns we insert; omit DB-default-only).
SEED_LOAD_COLUMNS: dict[tuple[str, str], frozenset[str]] = {
    ("ecommerce", "categories"): frozenset({"id", "name", "description"}),
    ("ecommerce", "customers"): frozenset({"id", "name", "email", "location"}),
    ("ecommerce", "products"): frozenset({"id", "name", "price", "category_id"}),
    ("ecommerce", "orders"): frozenset({"id", "customer_id", "order_date", "total_value"}),
    ("support", "customers"): frozenset(
        {"id", "name", "email", "contact_info", "account_status"}
    ),
    ("support", "agents"): frozenset({"id", "name", "department", "email"}),
    ("support", "tickets"): frozenset(
        {"id", "title", "description", "customer_id", "status", "priority"}
    ),
    ("support", "ticket_notes"): frozenset(
        {"id", "ticket_id", "agent_id", "note", "created_at"}
    ),
}


class DataLoader:   
    def __init__(self):
        self.engine = engine
        self.session = SessionLocal()
    
    def setup_schemas(self):
        with self.engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ecommerce"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS support"))
    
    def create_tables(self):
        import db.models

        Base.metadata.create_all(bind=self.engine)

    def ensure_customer_columns(self) -> None:
        """Migrate existing DBs: columns added after first deploy (matches sample CSVs)."""
        stmts = [
            "ALTER TABLE ecommerce.customers ADD COLUMN IF NOT EXISTS location VARCHAR(255)",
            "ALTER TABLE support.customers ADD COLUMN IF NOT EXISTS contact_info VARCHAR(512)",
            "ALTER TABLE support.customers ADD COLUMN IF NOT EXISTS account_status VARCHAR(64)",
        ]
        with self.engine.begin() as conn:
            for sql in stmts:
                conn.execute(text(sql))
    
    def create_indexes(self):
        index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON ecommerce.orders(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_date ON ecommerce.orders(order_date)",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON ecommerce.orders(customer_id, order_date DESC)",
            "CREATE INDEX IF NOT EXISTS idx_products_category ON ecommerce.products(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON support.tickets(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON support.tickets(status)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_priority ON support.tickets(priority)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_notes_ticket_id ON support.ticket_notes(ticket_id)",
        ]
        
        with self.engine.begin() as conn:
            for sql in index_sql:
                conn.execute(text(sql))
    
    def load_csv(
        self,
        file_path: str,
        schema: str,
        table: str
    ) -> Dict[str, Any]:
        
        try:
            df = pd.read_csv(file_path)
            
            df.columns = [col.lower().replace(' ', '_').replace('-', '_')
                         for col in df.columns]

            df = self._shape_dataframe(df, schema, table)
            df = self._keep_model_columns(df, schema, table)
            df = self._convert_types(df)
            
            errors = self._validate_data(df, schema, table)
            if errors:
                for error in errors:
                    logger.warning("%s.%s: %s", schema, table, error)
            
            table_name = f"{schema}.{table}"
            df.to_sql(
                table,
                con=self.engine,
                schema=schema,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=100
            )
            
            return {
                "table": table_name,
                "rows_loaded": len(df),
                "columns": list(df.columns),
                "errors": errors
            }
        
        except Exception as e:
            logger.warning("load_csv failed %s.%s: %s", schema, table, e)
            raise
    
    def _shape_dataframe(self, df: pd.DataFrame, schema: str, table: str) -> pd.DataFrame:
        """Align sample CSV columns with SQLAlchemy models before load."""
        df = df.copy()
        if schema == "ecommerce" and table == "orders":
            if "total_amount" in df.columns and "total_value" not in df.columns:
                df = df.rename(columns={"total_amount": "total_value"})
        if schema == "ecommerce" and table == "products":
            if "description" in df.columns:
                df = df.drop(columns=["description"])
        if schema == "support" and table == "agents":
            if "expertise" in df.columns:
                df = df.drop(columns=["expertise"])
            if "email" not in df.columns and "id" in df.columns:
                df["email"] = df["id"].apply(
                    lambda x: f"agent_{int(x)}@example.local" if pd.notna(x) else None
                )
        if schema == "support" and table == "ticket_notes":
            if "notes" in df.columns and "note" not in df.columns:
                df = df.rename(columns={"notes": "note"})
            if "timestamp" in df.columns and "created_at" not in df.columns:
                df = df.rename(columns={"timestamp": "created_at"})
        return df

    def _keep_model_columns(
        self, df: pd.DataFrame, schema: str, table: str
    ) -> pd.DataFrame:
        """Only keep columns that exist on the ORM table for this load."""
        key = (schema, table)
        allowed = SEED_LOAD_COLUMNS.get(key)
        if not allowed:
            return df
        extras = [c for c in df.columns if c not in allowed]
        for c in extras:
            logger.warning("seed: dropping unknown column %s.%s.%s", schema, table, c)
        keep = [c for c in df.columns if c in allowed]
        return df[keep].copy() if keep else df

    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if "price" in col or "total" in col or "value" in col:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            elif "date" in col or "created" in col or "updated" in col:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif col == "id" or col.endswith("_id"):
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        return df
    
    def _validate_data(self, df: pd.DataFrame, schema: str, table: str) -> List[str]:
        errors = []
        
        required = {
            ('ecommerce', 'customers'): ['name', 'email'],
            ('ecommerce', 'products'): ['name', 'price'],
            ('ecommerce', 'orders'): ['customer_id', 'order_date', 'total_value'],
            ('support', 'customers'): ['name', 'email'],
            ('support', 'tickets'): ['customer_id', 'title', 'status'],
            ('support', 'agents'): ['name'],
            ('support', 'ticket_notes'): ['ticket_id', 'agent_id', 'note'],
        }
        
        for col in required.get((schema, table), []):
            if df[col].isnull().any():
                errors.append(f"Column '{col}' has {df[col].isnull().sum()} null values")
        
        return errors
    
    def clear_data(self):
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE support.ticket_notes CASCADE"))
            conn.execute(text("TRUNCATE support.tickets CASCADE"))
            conn.execute(text("TRUNCATE support.agents CASCADE"))
            conn.execute(text("TRUNCATE support.customers CASCADE"))
            conn.execute(text("TRUNCATE ecommerce.orders CASCADE"))
            conn.execute(text("TRUNCATE ecommerce.products CASCADE"))
            conn.execute(text("TRUNCATE ecommerce.categories CASCADE"))
            conn.execute(text("TRUNCATE ecommerce.customers CASCADE"))
    
    def load_all(
        self,
        data_dir: str | None = None,
        clear_first: bool = True,
    ) -> Dict[str, Any]:
        """
        Load bundled CSVs from ``backend/sample-data`` (ecommerce + support subfolders).
        Pass ``data_dir`` to override (absolute or relative to cwd).
        """
        if data_dir is None:
            data_dir = str(
                Path(__file__).resolve().parent.parent / "sample-data"
            )

        root = Path(data_dir)

        self.setup_schemas()
        self.create_tables()
        self.ensure_customer_columns()

        if clear_first and root.exists():
            self.clear_data()

        load_jobs: list[tuple[str, str, str]] = [
            ("ecommerce/ecom_categories.csv", "ecommerce", "categories"),
            ("ecommerce/ecom_customers.csv", "ecommerce", "customers"),
            ("ecommerce/ecom_products.csv", "ecommerce", "products"),
            ("ecommerce/ecom_orders.csv", "ecommerce", "orders"),
            ("support/support_customers.csv", "support", "customers"),
            ("support/support_agents.csv", "support", "agents"),
            ("support/support_tickets.csv", "support", "tickets"),
            ("support/support_interactions.csv", "support", "ticket_notes"),
        ]

        results: Dict[str, Any] = {}

        for rel_path, schema, table in load_jobs:
            file_path = root / rel_path
            if file_path.exists():
                result = self.load_csv(str(file_path), schema, table)
                results[f"{schema}.{table}"] = result
            else:
                logger.warning("seed: missing file %s", file_path)
        
        self.create_indexes()

        return results


def main():
    loader = DataLoader()
    results = loader.load_all()
    
    print("\n" + "="*60)
    print("LOAD SUMMARY")
    print("="*60)
    for table, result in results.items():
        print(f"{table}: {result['rows_loaded']} rows")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()