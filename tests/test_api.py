"""Tests for the natural-language SQL API endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from orders_analytics.api import app
from orders_analytics.database.connection import SQLExecutionError
from orders_analytics.services.llm import LLMService, LLMServiceError

client = TestClient(app)


def test_query_endpoint_returns_rows_for_valid_sql(monkeypatch) -> None:
    """The endpoint should return the result set produced by a validated read-only query."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        assert question
        return "SELECT * FROM sales_by_month_country LIMIT 1"

    def fake_execute_query(query: str) -> list[dict[str, object]]:
        assert query == "SELECT * FROM sales_by_month_country LIMIT 1"
        return [{"month": "2024-01", "country": "Spain", "total_amount": "2500.00"}]

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)
    monkeypatch.setattr("orders_analytics.api.execute_read_only_query", fake_execute_query)

    response = client.post("/query", json={"question": "What were sales by month and country?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "What were sales by month and country?"
    assert payload["sql"] == "SELECT * FROM sales_by_month_country LIMIT 1"
    assert payload["rows"] == [{"month": "2024-01", "country": "Spain", "total_amount": "2500.00"}]


def test_query_endpoint_rejects_unauthorized_sql(monkeypatch) -> None:
    """The endpoint must reject SQL that tries to access unapproved tables."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        return "SELECT * FROM orders"

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)

    response = client.post("/query", json={"question": "Show all orders"})

    assert response.status_code == 422
    assert "security policy" in response.json()["detail"].lower()
    assert "unauthorized" in response.json()["detail"].lower()
    assert response.json()["attempted_sql"] is None
    assert response.json()["attempted_sql_redacted"] is True


def test_query_endpoint_includes_safe_attempted_sql_for_validation_errors(monkeypatch) -> None:
    """A rejected query over approved views should be included for debugging."""
    attempted_sql = (
        "SELECT month FROM sales_by_month_country UNION SELECT customer FROM top_customers"
    )

    def fake_generate_sql(self: LLMService, question: str) -> str:
        return attempted_sql

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)

    response = client.post("/query", json={"question": "Show monthly sales"})

    assert response.status_code == 422
    assert "only select statements" in response.json()["detail"].lower()
    assert response.json()["attempted_sql"] == attempted_sql
    assert response.json()["attempted_sql_redacted"] is False


def test_query_endpoint_describes_invalid_sql_syntax(monkeypatch) -> None:
    """Malformed model output should return a safe, explicit client error."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        return "SELEC * FROM sales_by_month_country"

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)

    response = client.post("/query", json={"question": "Show sales"})

    assert response.status_code == 422
    assert "invalid syntax" in response.json()["detail"].lower()
    assert response.json()["attempted_sql"] is None
    assert response.json()["attempted_sql_redacted"] is True


def test_query_endpoint_surfaces_llm_failures(monkeypatch) -> None:
    """LLM generation failures should map to an explicit HTTP 502 response."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        raise LLMServiceError(
            "The LLM provider request failed (APIConnectionError). "
            "Check provider availability and configuration."
        )

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)

    response = client.post("/query", json={"question": "Show the top customers"})

    assert response.status_code == 502
    assert "llm" in response.json()["detail"].lower()
    assert "apiconnectionerror" in response.json()["detail"].lower()
    assert response.json()["attempted_sql"] is None
    assert response.json()["attempted_sql_redacted"] is False


def test_query_endpoint_describes_invalid_generated_columns(monkeypatch) -> None:
    """Unknown view columns should be a safe client error, not a database outage."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        return "SELECT * FROM sales_by_month_country"

    def fake_execute_query(query: str) -> list[dict[str, object]]:
        raise SQLExecutionError(
            "SQLite reported no such column: internal_column",
            public_message=(
                "Generated SQL references a column that is not available in the "
                "approved analytical views."
            ),
            status_code=422,
        )

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)
    monkeypatch.setattr("orders_analytics.api.execute_read_only_query", fake_execute_query)

    response = client.post("/query", json={"question": "Show sales"})

    assert response.status_code == 422
    assert "column" in response.json()["detail"].lower()
    assert "internal_column" not in response.json()["detail"]
    assert response.json()["attempted_sql"] == "SELECT * FROM sales_by_month_country"


def test_query_endpoint_does_not_expose_database_errors(monkeypatch) -> None:
    """Database failures should return a safe message instead of internal details."""

    def fake_generate_sql(self: LLMService, question: str) -> str:
        return "SELECT * FROM sales_by_month_country"

    def fake_execute_query(query: str) -> list[dict[str, object]]:
        raise SQLExecutionError("Database file unavailable at C:/private/orders.db")

    monkeypatch.setattr(LLMService, "generate_sql", fake_generate_sql)
    monkeypatch.setattr("orders_analytics.api.execute_read_only_query", fake_execute_query)

    response = client.post("/query", json={"question": "Show sales"})

    assert response.status_code == 503
    assert "C:/private/orders.db" not in response.json()["detail"]
    assert response.json()["attempted_sql"] == "SELECT * FROM sales_by_month_country"
