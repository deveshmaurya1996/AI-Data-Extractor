from ai.query_normalizer import normalize_query_for_extraction


def test_fata_to_data_in_related_context():
    q = "ok show me all fata related to Alice"
    n = normalize_query_for_extraction(q)
    assert "fata" not in n.lower()
    assert "data" in n.lower()


def test_collapses_whitespace():
    assert normalize_query_for_extraction("a   b") == "a b"
