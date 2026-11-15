"""Tests for the SQL validation guardrails and approved analytical views."""

from __future__ import annotations

import pytest

from orders_analytics.sql.validation import SQLValidationError, validate_sql_query
from orders_analytics.sql.views import (
    SALES_BY_MONTH_COUNTRY_VIEW_SQL,
    TOP_CUSTOMERS_VIEW_SQL,
    VALID_VIEW_STATEMENTS,
)


def test_valid_view_queries_are_accepted() -> None:
    """Approved read-only queries against the analytical views should pass validation."""
    valid_queries = [
        "SELECT * FROM sales_by_month_country",
        "SELECT customer, total_amount FROM top_customers WHERE total_amount > 1000",
    ]

    for query in valid_queries:
        validated = validate_sql_query(query)
        assert "SELECT" in validated.upper()

    assert "sales_by_month_country" in SALES_BY_MONTH_COUNTRY_VIEW_SQL.lower()
    assert "top_customers" in TOP_CUSTOMERS_VIEW_SQL.lower()
    assert set(VALID_VIEW_STATEMENTS) == {"sales_by_month_country", "top_customers"}


def test_invalid_sql_is_rejected() -> None:
    """Only a single SELECT against the approved views should be accepted."""
    invalid_queries = [
        "INSERT INTO orders VALUES (1, 'x')",
        "SELECT * FROM orders; SELECT * FROM sales_by_month_country",
        "SELECT * FROM users",
    ]

    for query in invalid_queries:
        with pytest.raises(SQLValidationError):
            validate_sql_query(query)


def test_unapproved_sql_ddl_and_multiple_statements_are_blocked() -> None:
    """The guardrails must reject DDL and multiple SQL statements before execution."""
    with pytest.raises(SQLValidationError):
        validate_sql_query("DROP TABLE orders")

    with pytest.raises(SQLValidationError):
        validate_sql_query("SELECT * FROM sales_by_month_country; DROP TABLE orders")
