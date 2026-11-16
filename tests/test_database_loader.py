"""Tests for loading cleaned orders into SQLite and materializing the analytical views."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from orders_analytics.config import settings
from orders_analytics.database.connection import (
    SQLExecutionError,
    _database_path_from_url,
    execute_read_only_query,
)
from orders_analytics.database.loader import load_orders_db


def test_load_orders_db_persists_clean_csv_and_materializes_views(tmp_path, monkeypatch) -> None:
    """The loader should insert the cleaned rows and create both approved analytical views."""
    csv_path = tmp_path / "orders_clean.csv"
    database_path = tmp_path / "orders.db"

    pd.DataFrame(
        [
            {
                "date": "2024-01-15",
                "customer": "Ana García",
                "country": "Spain",
                "product": "Laptop Pro",
                "amount": "1500.00",
                "status": "paid",
            },
            {
                "date": "2024-01-20",
                "customer": "Carlos Silva",
                "country": "Spain",
                "product": "Tablet Air",
                "amount": "275.50",
                "status": "shipped",
            },
            {
                "date": "2024-02-02",
                "customer": "Ana García",
                "country": "Mexico",
                "product": "Keyboard Ergo",
                "amount": "95.00",
                "status": "paid",
            },
        ]
    ).to_csv(csv_path, index=False)

    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    loaded_path = load_orders_db(input_path=csv_path)

    assert loaded_path == database_path
    assert database_path.exists()

    orders = execute_read_only_query("SELECT COUNT(*) AS row_count FROM orders")
    assert orders == [{"row_count": 3}]

    sales = execute_read_only_query(
        "SELECT month, country, total_amount FROM sales_by_month_country ORDER BY month, country"
    )
    assert sales == [
        {"month": "2024-01", "country": "Spain", "total_amount": "1775.50"},
        {"month": "2024-02", "country": "Mexico", "total_amount": "95.00"},
    ]

    customers = execute_read_only_query("SELECT customer, total_amount FROM top_customers")
    assert customers == [
        {"customer": "Ana García", "total_amount": "1595.00"},
        {"customer": "Carlos Silva", "total_amount": "275.50"},
    ]


def test_views_sum_minor_units_and_sort_customers_numerically(tmp_path) -> None:
    """Analytical view totals should preserve cents and use numeric rank order."""
    csv_path = tmp_path / "orders_clean.csv"
    database_path = tmp_path / "orders.db"
    rows = [
        {
            "date": "2024-01-01",
            "customer": "Small Buyer",
            "country": "Spain",
            "product": "Item",
            "amount": "0.01",
            "status": "paid",
        }
        for _ in range(100)
    ]
    rows.append(
        {
            "date": "2024-01-01",
            "customer": "Large Buyer",
            "country": "Spain",
            "product": "Item",
            "amount": "10.00",
            "status": "paid",
        }
    )
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    load_orders_db(
        input_path=csv_path,
        database_url=f"sqlite:///{database_path.as_posix()}",
    )
    customers = execute_read_only_query(
        "SELECT customer, total_amount FROM top_customers",
        database_url=f"sqlite:///{database_path.as_posix()}",
    )
    assert customers == [
        {"customer": "Large Buyer", "total_amount": "10.00"},
        {"customer": "Small Buyer", "total_amount": "1.00"},
    ]


def test_views_preserve_sign_for_negative_subunit_totals(tmp_path) -> None:
    """Negative amounts below one currency unit must retain their sign in both views."""
    csv_path = tmp_path / "orders_clean.csv"
    database_path = tmp_path / "orders.db"
    pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "customer": "Refund Customer",
                "country": "Spain",
                "product": "Item",
                "amount": "-0.49",
                "status": "returned",
            }
        ]
    ).to_csv(csv_path, index=False)

    load_orders_db(
        input_path=csv_path,
        database_url=f"sqlite:///{database_path.as_posix()}",
    )

    monthly_total = execute_read_only_query(
        "SELECT total_amount FROM sales_by_month_country",
        database_url=f"sqlite:///{database_path.as_posix()}",
    )
    customer_total = execute_read_only_query(
        "SELECT total_amount FROM top_customers",
        database_url=f"sqlite:///{database_path.as_posix()}",
    )
    assert monthly_total == [{"total_amount": "-0.49"}]
    assert customer_total == [{"total_amount": "-0.49"}]


def test_relative_database_urls_resolve_from_the_project_root(tmp_path) -> None:
    """Relative SQLite URIs should resolve under the repository root, not the drive root."""
    project_root = Path(__file__).resolve().parents[1]
    relative_db = project_root / "data" / "database" / "orders.db"
    relative_db.parent.mkdir(parents=True, exist_ok=True)
    relative_db.touch()

    assert _database_path_from_url("sqlite:///./data/database/orders.db") == relative_db
    assert _database_path_from_url("sqlite:///data/database/orders.db") == relative_db

    absolute_db = tmp_path / "absolute.db"
    absolute_db.touch()
    assert _database_path_from_url(f"sqlite:///{absolute_db.as_posix()}") == absolute_db

    with pytest.raises(SQLExecutionError):
        _database_path_from_url("sqlite:///:memory:")


def test_execute_read_only_query_rejects_memory_and_empty_sql() -> None:
    """The execution helper must reject in-memory databases and empty queries before execution."""
    with pytest.raises(SQLExecutionError):
        execute_read_only_query("SELECT 1", database_url="sqlite:///:memory:")

    with pytest.raises(SQLExecutionError):
        execute_read_only_query("   ")


def test_execute_read_only_query_enforces_result_limit(tmp_path, monkeypatch) -> None:
    """The execution helper should reject oversized results instead of silently truncating them."""
    database_path = tmp_path / "orders.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE VIEW sales_by_month_country AS "
            "SELECT 1 AS month UNION ALL SELECT 2 UNION ALL SELECT 3"
        )
    monkeypatch.setattr(settings, "SQLITE_MAX_RESULT_ROWS", 2)

    with pytest.raises(SQLExecutionError) as error:
        execute_read_only_query(
            "SELECT month FROM sales_by_month_country",
            database_url=f"sqlite:///{database_path.as_posix()}",
        )

    assert error.value.status_code == 422
    assert "maximum" in error.value.public_message.lower()


def test_execute_read_only_query_enforces_execution_timeout(tmp_path, monkeypatch) -> None:
    """The execution helper should interrupt long-running SQLite queries."""
    database_path = tmp_path / "orders.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE VIEW sales_by_month_country AS SELECT 1 AS month")
    monkeypatch.setattr(settings, "SQLITE_QUERY_TIMEOUT_SECONDS", 0.000001)
    monkeypatch.setattr(settings, "SQLITE_MAX_RESULT_ROWS", 2_000_000)

    with pytest.raises(SQLExecutionError) as error:
        execute_read_only_query(
            "WITH RECURSIVE seq(value) AS ("
            "SELECT month FROM sales_by_month_country "
            "UNION ALL SELECT value + 1 FROM seq WHERE value < 1000000"
            ") SELECT value FROM seq",
            database_url=f"sqlite:///{database_path.as_posix()}",
        )

    assert error.value.status_code == 504
    assert "time limit" in error.value.public_message.lower()


def test_execute_read_only_query_classifies_unknown_columns_as_invalid_sql(tmp_path) -> None:
    """Unknown view columns should be categorized without exposing SQLite internals."""
    database_path = tmp_path / "orders.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE sales_by_month_country (month TEXT)")

    with pytest.raises(SQLExecutionError) as error:
        execute_read_only_query(
            "SELECT unknown_column FROM sales_by_month_country",
            database_url=f"sqlite:///{database_path.as_posix()}",
        )

    assert error.value.status_code == 422
    assert "column" in error.value.public_message.lower()
    assert "unknown_column" not in error.value.public_message


def test_load_orders_db_raises_for_missing_required_columns(tmp_path) -> None:
    """The loader should fail fast if a cleaned CSV lacks the required fields."""
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame([{"date": "2024-01-15", "customer": "Ana"}]).to_csv(csv_path, index=False)

    try:
        load_orders_db(
            input_path=csv_path,
            database_url=f"sqlite:///{(tmp_path / 'bad.db').as_posix()}",
        )
        raise AssertionError("Expected a ValueError for a missing required column")
    except ValueError as exc:
        assert "missing required columns" in str(exc).lower()
