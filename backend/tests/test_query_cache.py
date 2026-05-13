from services import query_cache


def test_cache_roundtrip():
    sql = "SET statement_timeout TO 5000;\nSELECT 1 AS n LIMIT 1000;"
    rows = [{"n": 1}]
    query_cache.set_cached("conv-a", sql, rows)
    got = query_cache.get_cached("conv-a", sql)
    assert got == rows


def test_cache_miss_different_conversation():
    sql = "SET statement_timeout TO 5000;\nSELECT 1 LIMIT 1000;"
    query_cache.set_cached("c1", sql, [{"x": 1}])
    assert query_cache.get_cached("c2", sql) is None


def test_invalidate_conversation():
    sql = "SET statement_timeout TO 5000;\nSELECT 2 LIMIT 1000;"
    query_cache.set_cached("keep", sql, [{"a": 1}])
    query_cache.set_cached("drop", sql, [{"b": 2}])
    query_cache.invalidate_conversation("drop")
    assert query_cache.get_cached("drop", sql) is None
    assert query_cache.get_cached("keep", sql) is not None
