
from ai.formatter import ResponseFormatter


def test_formatter_echoes_supplied_message_verbatim():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="Custom LLM message about the rows.",
        data=[{"a": 1}, {"a": 2}],
        sql="SELECT 1",
        strategy="template",
        confidence=0.9,
    )
    assert response.message == "Custom LLM message about the rows."


def test_formatter_preserves_message_for_empty_data():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="No rows matched. Try widening the date range.",
        data=[],
        sql="SELECT 1",
        strategy="template",
        confidence=0.9,
    )
    assert response.message == "No rows matched. Try widening the date range."
    assert response.metadata["row_count"] == 0
    assert response.metadata["data_preview"] == []


def test_formatter_attaches_row_count_and_preview():
    formatter = ResponseFormatter()
    data = [{"n": i} for i in range(8)]
    response = formatter.format(
        message="Eight rows returned.",
        data=data,
        sql="SELECT 1",
        strategy="template",
        confidence=0.9,
    )
    assert response.metadata["row_count"] == 8
    assert response.metadata["data_preview"] == data[:5]


def test_formatter_used_uploads_explanation():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="One row from your uploaded sheet.",
        data=[{"x": 1}],
        sql="SELECT 1",
        strategy="ai_fallback",
        confidence=0.7,
        used_uploads=True,
    )
    assert "upload" in response.metadata["explanation"].lower()
    assert response.metadata["used_uploads"] is True


def test_formatter_plan_built_explanation():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="One row found.",
        data=[{"a": 1}],
        sql="SELECT 1",
        strategy="plan_built",
        confidence=1.0,
    )
    assert "deterministic" in response.metadata["explanation"].lower()


def test_formatter_template_explanation():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="One row found.",
        data=[{"a": 1}],
        sql="SELECT 1",
        strategy="template",
        confidence=1.0,
    )
    assert "template" in response.metadata["explanation"].lower()


def test_formatter_confidence_labels():
    formatter = ResponseFormatter()
    for confidence, label in [(0.95, "high"), (0.7, "medium"), (0.3, "low")]:
        response = formatter.format(
            message="ok",
            data=[],
            sql="SELECT 1",
            strategy="template",
            confidence=confidence,
        )
        assert response.metadata["confidence_label"] == label


def test_formatter_metadata_contains_sql_and_strategy():
    formatter = ResponseFormatter()
    response = formatter.format(
        message="ok",
        data=[],
        sql="SELECT * FROM ecommerce.orders LIMIT 1",
        strategy="plan_built",
        confidence=0.8,
    )
    assert response.metadata["sql"] == "SELECT * FROM ecommerce.orders LIMIT 1"
    assert response.metadata["strategy"] == "plan_built"
    assert response.metadata["confidence"] == 0.8
