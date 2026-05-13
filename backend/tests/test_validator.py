from ai.validator import SQLValidator, query_policy_lines


def test_validator_blocks_write_query():
    validator = SQLValidator()
    result = validator.validate("DELETE FROM orders")
    assert result.is_safe is False


def test_validator_allows_created_at_not_create_keyword():
    """Substring 'CREATE' inside identifier created_at must not false-positive."""
    validator = SQLValidator()
    sql = """
    SELECT c.id, c.created_at
    FROM ecommerce.customers c
    ORDER BY c.created_at DESC
    LIMIT 10;
    """
    result = validator.validate(sql)
    assert result.is_safe is True
    assert result.sql_safe is not None


def test_validator_blocks_literal_create_statement():
    validator = SQLValidator()
    result = validator.validate("CREATE TABLE foo (id int)")
    assert result.is_safe is False
    assert "CREATE" in (result.reason or "")


def test_validator_blocks_id_cast_to_timestamp():
    validator = SQLValidator()
    sql = """
    SELECT c.id::text AS id, c.created_at
    FROM ecommerce.customers c
    UNION ALL
    SELECT cat.id::text, cat.id::text::timestamp
    FROM ecommerce.categories cat;
    """
    result = validator.validate(sql)
    assert result.is_safe is False
    assert "timestamp" in (result.error or "").lower() or "cast" in (
        result.reason or ""
    ).lower()


def test_validator_allows_literal_timestamp_cast():
    """Legitimate timestamp casts on literals or real time columns stay allowed."""
    validator = SQLValidator()
    sql = """
    SELECT '2020-01-01'::text::timestamp AS ts
    FROM ecommerce.customers c
    LIMIT 1;
    """
    result = validator.validate(sql)
    assert result.is_safe is True


def test_query_policy_lines_nonempty():
    lines = query_policy_lines()
    assert len(lines) >= 3
    assert "SELECT" in "\n".join(lines)
    assert "DELETE" in "\n".join(lines)


def test_validator_constructor_overrides_limits():
    v = SQLValidator(max_rows=7, query_timeout_ms=1234)
    r = v.validate("SELECT 1 FROM ecommerce.customers")
    assert r.is_safe is True
    assert r.sql_safe is not None
    assert "LIMIT 7" in r.sql_safe
    assert "statement_timeout TO 1234" in r.sql_safe
