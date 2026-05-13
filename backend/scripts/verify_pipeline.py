
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _bootstrap() -> None:
    os.chdir(BACKEND_ROOT)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")


async def _main() -> int:
    _bootstrap()

    print("Step 1: Pollinations chat API ...")
    try:
        from ai.pollinations_client import complete_text

        ping = (
            await complete_text(
                system='Reply with exactly one word: "pong". No other text.',
                user="Ping.",
            )
        ).strip()
        print(f"  → {ping!r}")
        if "pong" not in ping.lower():
            print("  WARN: unexpected reply (check POLLINATIONS_API_KEY / POLLINATIONS_MODEL).")
    except Exception as e:
        print(f"  SKIP (Pollinations unavailable): {e}")
        print("  Seeding and template-based chat will still run.")

    print("\nStep 2: Seed database from sample-data ...")
    from db.seed import DataLoader

    loader = DataLoader()
    results = loader.load_all(clear_first=True)
    if not results:
        print("  ERROR: no tables loaded — check sample-data paths.")
        return 1
    for key, meta in results.items():
        print(f"  {key}: {meta.get('rows_loaded', 0)} rows")

    print("\nStep 3: DB read + template SQL (same path as chat, no LLM) ...")
    from sqlalchemy import text
    from db.engine import SessionLocal
    from ai.query_templates import TemplateQueryExecutor
    from ai.validator import SQLValidator
    from ai.executor import QueryExecutor

    db = SessionLocal()
    try:
        n_orders = db.execute(
            text("SELECT COUNT(*) FROM ecommerce.orders")
        ).scalar_one()
        n_tickets = db.execute(
            text("SELECT COUNT(*) FROM support.tickets")
        ).scalar_one()
        print(f"  ecommerce.orders rows={n_orders}, support.tickets rows={n_tickets}")
        if int(n_orders) < 1 or int(n_tickets) < 1:
            print("  ERROR: expected seeded rows in both domains.")
            return 1

        tpl = TemplateQueryExecutor()
        gen = tpl.execute("customer_orders_all", {"customer_id": 1})
        if not gen.success or gen.sql is None:
            print(f"  ERROR template: {gen.error}")
            return 1
        val = SQLValidator().validate(gen.sql)
        if not val.is_safe or val.sql_safe is None:
            print(f"  ERROR validate: {val.error}")
            return 1
        run = QueryExecutor(db).execute(val.sql_safe)
        if not run.success:
            print(f"  ERROR execute: {run.error}")
            return 1
        print(f"  template customer_orders_all → {run.row_count} row(s) sample={run.data[:2]}")

        print("\nStep 4: Full chat (cross-domain template SQL; LLM is required for the user-facing summary) ...")
        from services.chat_service import ChatService

        svc = ChatService()
        resp = await svc.handle_query(
            "Find customers who have made purchases but never raised support tickets",
            db,
        )
        print(f"  type={resp.type}")
        if resp.type == "error":
            print(f"  message={getattr(resp, 'message', '')[:400]!r}")
            return 1
        print(f"  message={getattr(resp, 'message', '')[:300]!r}")
    finally:
        db.close()

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
