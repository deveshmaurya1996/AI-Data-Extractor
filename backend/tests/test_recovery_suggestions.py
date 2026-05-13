from ai.interfaces import EntityExtractionResult
from services.recovery_suggestions import build_recovery_suggestions


def test_recovery_rewrites_spoken_to_canonical():
    entities = EntityExtractionResult(
        customer_name="Hina Patel",
        customer_candidates=[
            {"id": 8, "name": "Hina Patel", "schema": "ecommerce"},
        ],
        time_period="1_months",
        keywords=["order"],
        requires_clarification=False,
        spoken_customer_term="hina",
    )
    q = "Show me all orders from customer hina in the last month"
    out = build_recovery_suggestions(None, q, entities)
    assert out[0] == "Show me all orders from customer Hina Patel in the last month"


def test_recovery_widens_time_when_period_set():
    entities = EntityExtractionResult(
        customer_name="Hina Patel",
        customer_candidates=[
            {"id": 8, "name": "Hina Patel", "schema": "ecommerce"},
        ],
        time_period="1_months",
        keywords=["order"],
        requires_clarification=False,
        spoken_customer_term="hina",
    )
    q = "Show me all orders from customer hina in the last month"
    out = build_recovery_suggestions(None, q, entities)
    assert len(out) >= 2
    assert any("last month" not in s.lower() for s in out)


def test_recovery_fuzzy_without_candidates_uses_db(monkeypatch):
    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return [
                {"id": 8, "name": "Hina Patel", "schema": "ecommerce"},
            ]

    class FakeDB:
        def execute(self, *args, **kwargs):
            return FakeResult()

    entities = EntityExtractionResult(
        customer_name=None,
        customer_candidates=[],
        time_period=None,
        keywords=["order"],
        requires_clarification=False,
        spoken_customer_term="hina",
    )
    q = "Show orders for customer hina"
    out = build_recovery_suggestions(FakeDB(), q, entities)
    assert out and "Hina Patel" in out[0]
