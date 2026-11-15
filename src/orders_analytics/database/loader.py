"""Database initialization helpers for the cleaned orders dataset."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from orders_analytics.config import settings
from orders_analytics.data.generation import ORDER_COLUMNS
from orders_analytics.sql.views import (
    SALES_BY_MONTH_COUNTRY_VIEW_SQL,
    TOP_CUSTOMERS_VIEW_SQL,
)


def _database_path_from_url(database_url: str) -> Path:
    """Resolve a SQLite URL into a local filesystem path."""
    if database_url.startswith("sqlite:///:memory:") or database_url.endswith(":memory:"):
        raise ValueError("In-memory SQLite databases are not supported for this loader.")

    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise ValueError(f"Unsupported database scheme: {parsed.scheme!r}.")

    path_text = parsed.path
    if path_text in {"", ":memory:"}:
        raise ValueError("A database file path is required for SQLite persistence.")

    project_root = Path(__file__).resolve().parents[3]
    if (
        len(path_text) >= 3
        and path_text.startswith("/")
        and path_text[1].isalpha()
        and path_text[2] == ":"
    ):
        path_text = path_text[1:]
    elif path_text.startswith("//"):
        path_text = path_text[1:]
    else:
        path_text = path_text.lstrip("/")

    database_path = Path(path_text)
    if not database_path.is_absolute():
        database_path = (project_root / database_path).resolve()

    database_path.parent.mkdir(parents=True, exist_ok=True)
    return database_path


def load_orders_db(
    input_path: str | Path = Path("data/cleaned/orders_clean.csv"),
    database_url: str | None = None,
) -> Path:
    """Load the cleaned order CSV into SQLite and materialize the approved analytical views."""
    source_path = Path(input_path)
    if not source_path.exists():
        raise FileNotFoundError(f"The cleaned CSV does not exist: {source_path}")

    target_url = database_url or settings.database_url
    database_path = _database_path_from_url(target_url)

    dataframe = pd.read_csv(source_path)
    missing_columns = [column for column in ORDER_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"The CSV is missing required columns: {missing}")

    cleaned_frame = dataframe.loc[:, ORDER_COLUMNS].copy()
    cleaned_frame["amount"] = cleaned_frame["amount"].map(
        lambda value: str(Decimal(str(value)).quantize(Decimal("0.01")))
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP VIEW IF EXISTS sales_by_month_country")
        connection.execute("DROP VIEW IF EXISTS top_customers")
        connection.execute("DROP TABLE IF EXISTS orders")
        connection.execute(
            """
            CREATE TABLE orders (
                date TEXT NOT NULL,
                customer TEXT NOT NULL,
                country TEXT NOT NULL,
                product TEXT NOT NULL,
                amount TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO orders (date, customer, country, product, amount, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [tuple(row) for row in cleaned_frame.itertuples(index=False, name=None)],
        )

        connection.executescript(
            f"""
            DROP VIEW IF EXISTS sales_by_month_country;
            {SALES_BY_MONTH_COUNTRY_VIEW_SQL};
            DROP VIEW IF EXISTS top_customers;
            {TOP_CUSTOMERS_VIEW_SQL};
            """
        )
        connection.commit()

    return database_path
