"""Tests for loading cleaned orders into SQLite and materializing the analytical views."""

from __future__ import annotations

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

    customers = execute_read_only_query(
        "SELECT customer, total_amount FROM top_customers ORDER BY total_amount DESC, customer"
    )
    assert customers == [
        {"customer": "Carlos Silva", "total_amount": "275.50"},
        {"customer": "Ana García", "total_amount": "1595.00"},
    ]


def test_relative_database_urls_resolve_from_the_project_root(tmp_path) -> None:
    """Relative SQLite URIs should resolve under the repository root, not the drive root."""
    project_root = Path(__file__).resolve().parents[1]

    assert _database_path_from_url("sqlite:///./data/database/orders.db") == (
        project_root / "data" / "database" / "orders.db"
    )
    assert _database_path_from_url("sqlite:///data/database/orders.db") == (
        project_root / "data" / "database" / "orders.db"
    )

    absolute_db = tmp_path / "absolute.db"
    absolute_db.touch()
    assert _database_path_from_url(f"sqlite:///{absolute_db.as_posix()}") == absolute_db

    with pytest.raises(SQLExecutionError):
        _database_path_from_url("sqlite:///:memory:")


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
