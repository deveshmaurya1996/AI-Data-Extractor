from ai.executor import strip_all_null_columns


def test_strip_all_null_columns_removes_phantom_column():
    rows = [
        {"a": 1, "b": None, "c": 3},
        {"a": 2, "b": None, "c": 4},
    ]
    out = strip_all_null_columns(rows)
    assert out == [{"a": 1, "c": 3}, {"a": 2, "c": 4}]


def test_strip_all_null_columns_empty_input():
    assert strip_all_null_columns([]) == []
