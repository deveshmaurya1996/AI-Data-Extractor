from unittest.mock import MagicMock

from ai.entity_extractor import EntityExtractor


def _mock_db(rows: list[tuple]):
    db = MagicMock()
    db.execute.return_value = rows
    return db


def test_entity_extractor_smoke():
    db = MagicMock()
    db.execute.return_value = []
    extractor = EntityExtractor(db)
    result = extractor.extract("Show orders for John Smith")
    assert hasattr(result, "requires_clarification")


def test_extract_customer_tail_of_alice():
    db = _mock_db([(1, "Alice Chen", "alice.chen@example.com", "ecommerce")])
    r = EntityExtractor(db).extract("how much total purchase amount of alice")
    assert r.customer_name == "Alice Chen"
    assert len(r.customer_candidates) == 1
    assert r.spoken_customer_term == "alice"


def test_extract_the_alice_email():
    db = _mock_db([(1, "Alice Chen", "alice.chen@example.com", "ecommerce")])
    r = EntityExtractor(db).extract("show me the alice email")
    assert r.customer_name == "Alice Chen"


def test_extract_name_is_alice_chen():
    db = _mock_db([(1, "Alice Chen", "alice.chen@example.com", "ecommerce")])
    r = EntityExtractor(db).extract("actually name is Alice Chen")
    assert r.customer_name == "Alice Chen"
    assert len(r.customer_candidates) == 1


def test_list_of_orders_not_mistaken_for_name():
    db = _mock_db([])
    r = EntityExtractor(db).extract("give me a list of orders")
    assert r.customer_name is None
    assert r.customer_candidates == []
    assert r.spoken_customer_term is None


def test_spoken_preserved_when_no_db_match():
    db = _mock_db([])
    r = EntityExtractor(db).extract("orders for customer Zebraxxnotreal")
    assert r.customer_candidates == []
    assert r.spoken_customer_term == "zebraxxnotreal"


def test_show_me_alice_data_extracts_customer():
    db = _mock_db([(1, "Alice Chen", "alice.chen@example.com", "ecommerce")])
    r = EntityExtractor(db).extract("show me alice data")
    assert r.spoken_customer_term == "alice"
    assert len(r.customer_candidates) == 1
    assert r.customer_name == "Alice Chen"


def test_bare_full_name_extracts_customer():
    db = _mock_db([(1, "Alice Chen", "alice.chen@example.com", "ecommerce")])
    r = EntityExtractor(db).extract("Alice Chen")
    assert r.customer_name == "Alice Chen"
    assert len(r.customer_candidates) == 1


def test_cross_schema_duplicates_collapse_to_one_candidate():
    db = _mock_db(
        [
            (1, "Alice Chen", "alice.chen@example.com", "ecommerce"),
            (1, "Alice Chen", "alice.chen@example.com", "support"),
        ]
    )
    r = EntityExtractor(db).extract("show me alice data")
    assert len(r.customer_candidates) == 1
    c = r.customer_candidates[0]
    assert c.get("ecommerce_id") == 1
    assert c.get("support_id") == 1
    assert c.get("schema") == "both"
    assert r.requires_clarification is False

