"""Tests for deterministic dataset generation and raw-data cleaning."""

from __future__ import annotations

import pandas as pd

from orders_analytics.data.cleaning import clean_orders_csv, clean_orders_frame
from orders_analytics.data.generation import (
    ORDER_COLUMNS,
    generate_raw_orders_csv,
    generate_raw_orders_frame,
)


def test_generate_raw_orders_frame_has_required_columns_and_injected_invalid_rows() -> None:
    """The generated dataset must include the required schema and intentional data defects."""
    frame = generate_raw_orders_frame(row_count=1200, seed=42)

    assert list(frame.columns) == ORDER_COLUMNS
    assert len(frame) >= 1200
    assert (
        frame["date"].astype(str).str.contains("2024/04/31").any()
        or frame["date"].astype(str).str.contains("2024-15-03").any()
    )
    assert (frame["amount"].astype(str).str.strip() == "").any()
    assert (frame["status"].astype(str).str.upper() == "DELIVERED").any()


def test_generate_raw_orders_csv_writes_a_file(tmp_path) -> None:
    """The CSV generator should write the raw dataset to disk deterministically."""
    output_path = tmp_path / "raw_orders.csv"
    generated = generate_raw_orders_csv(output_path=output_path, row_count=1200, seed=42)

    assert output_path.exists()
    actual = pd.read_csv(output_path)
    assert list(actual.columns) == ORDER_COLUMNS
    assert len(actual) == len(generated)


def test_clean_orders_frame_removes_bad_rows_and_normalizes_values() -> None:
    """The cleaning layer must drop malformed rows and normalize valid values."""
    raw = pd.DataFrame(
        [
            {
                "date": "2024/04/31",
                "customer": " Ana García ",
                "country": " Spain ",
                "product": " Laptop Pro ",
                "amount": "",
                "status": "PAID",
            },
            {
                "date": "2024-03-05",
                "customer": "Ana García",
                "country": "Spain",
                "product": "Laptop Pro",
                "amount": "1250.500",
                "status": "PAID",
            },
            {
                "date": "2024-03-05",
                "customer": "Ana García",
                "country": "Spain",
                "product": "Laptop Pro",
                "amount": "1250.500",
                "status": "PAID",
            },
            {
                "date": "2024-02-01",
                "customer": "Carlos Silva",
                "country": "Mexico",
                "product": "Tablet Air",
                "amount": "49.99",
                "status": "shipped",
            },
        ]
    )

    cleaned = clean_orders_frame(raw)

    assert list(cleaned.columns) == ORDER_COLUMNS
    assert len(cleaned) == 2
    assert cleaned["date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
    assert cleaned["status"].str.fullmatch(r"[a-z]+").all()
    assert cleaned["amount"].str.contains(r"^\d+\.\d{2}$").all()
    assert not cleaned.duplicated().any()


def test_clean_orders_csv_reads_and_writes_file(tmp_path) -> None:
    """The CSV cleaning helper must read a raw dataset and write a cleaned result."""
    source = tmp_path / "orders_raw.csv"
    destination = tmp_path / "orders_clean.csv"
    source_frame = pd.DataFrame(
        [
            {
                "date": "2024-01-10",
                "customer": "Jane Doe",
                "country": "Spain",
                "product": "Laptop Pro",
                "amount": "510.00",
                "status": "paid",
            },
            {
                "date": "invalid",
                "customer": "Jane Doe",
                "country": "Spain",
                "product": "Laptop Pro",
                "amount": "",
                "status": "paid",
            },
        ]
    )
    source_frame.to_csv(source, index=False)

    cleaned = clean_orders_csv(input_path=source, output_path=destination)

    assert destination.exists()
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["date"] == "2024-01-10"
    assert cleaned.iloc[0]["amount"] == "510.00"
