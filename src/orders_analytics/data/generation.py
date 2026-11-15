"""Deterministic raw order-data generation for the challenge dataset."""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

ORDER_COLUMNS = ["date", "customer", "country", "product", "amount", "status"]


def _random_iso_date(rng: random.Random, min_year: int = 2024, max_year: int = 2025) -> str:
    """Generate a valid ISO-formatted date string using a fixed random seed."""
    start_day = date(min_year, 1, 1).toordinal()
    end_day = date(max_year, 12, 31).toordinal()
    picked_day = rng.randint(start_day, end_day)
    return date.fromordinal(picked_day).isoformat()


def _customer_name(rng: random.Random, index: int) -> str:
    """Return a deterministic customer name based on a seed and a counter."""
    pool = [
        "Ana García",
        "Daniel Ruiz",
        "Sofia Torres",
        "Mateo López",
        "Laura Pérez",
        "Carlos Silva",
        "Valeria Costa",
        "Javier Gómez",
        "Paula Romero",
        "Lucas Ortega",
        "Nora Díaz",
        "Hugo Morales",
    ]
    return pool[(index + rng.randint(0, len(pool) - 1)) % len(pool)]


def _product_name(rng: random.Random, index: int) -> str:
    """Return a deterministic product name based on a seed and a counter."""
    pool = [
        "Laptop Pro",
        "Tablet Air",
        "Monitor 4K",
        "Keyboard Ergo",
        "Mouse Wireless",
        "Printer Mini",
        "Desk Lamp",
        "USB Hub",
        "Headset Studio",
        "Webcam HD",
        "Speaker Mini",
        "Router Mesh",
    ]
    return pool[(index + rng.randint(0, len(pool) - 1)) % len(pool)]


def _country_name(rng: random.Random, index: int) -> str:
    """Return a deterministic country name based on a seed and a counter."""
    pool = [
        "Spain",
        "Mexico",
        "Argentina",
        "Chile",
        "Colombia",
        "Peru",
        "Brazil",
        "United States",
        "Germany",
        "France",
    ]
    return pool[(index + rng.randint(0, len(pool) - 1)) % len(pool)]


def _status_name(rng: random.Random, index: int) -> str:
    """Return a deterministic order status based on a seed and a counter."""
    pool = ["paid", "pending", "shipped", "cancelled", "returned"]
    return pool[(index + rng.randint(0, len(pool) - 1)) % len(pool)]


def generate_raw_orders_frame(row_count: int = 1200, seed: int = 42) -> pd.DataFrame:
    """Create a deterministic DataFrame with valid rows plus intentionally flawed records."""
    if row_count < 1000:
        raise ValueError("row_count must be at least 1000 to satisfy the challenge dataset requirement.")

    rng = random.Random(seed)
    rows: list[dict[str, str]] = []

    for index in range(row_count):
        record: dict[str, str] = {
            "date": _random_iso_date(rng),
            "customer": _customer_name(rng, index),
            "country": _country_name(rng, index),
            "product": _product_name(rng, index),
            "amount": str(
                (Decimal(rng.randint(100, 100000)) / Decimal("100")).quantize(Decimal("0.01"))
            ),
            "status": _status_name(rng, index),
        }

        if index == 0:
            record["date"] = "2024/04/31"
        if index == 1:
            record["amount"] = ""
        if index == 2:
            record["status"] = "DELIVERED"
        if index % 29 == 0 and index != 0:
            record["date"] = "2024-15-03"
        if index % 31 == 0:
            record["amount"] = ""
        if index % 43 == 0:
            record["customer"] = ""  # intentionally empty customer field
        if index % 47 == 0:
            rows.append(record.copy())

        rows.append(record)

    data_frame = pd.DataFrame(rows, columns=ORDER_COLUMNS)
    return data_frame


def generate_raw_orders_csv(
    output_path: str | Path = Path("data/raw/orders_raw.csv"),
    row_count: int = 1200,
    seed: int = 42,
) -> pd.DataFrame:
    """Persist a raw CSV file and return the generated DataFrame."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    raw_frame = generate_raw_orders_frame(row_count=row_count, seed=seed)
    raw_frame.to_csv(output, index=False)
    return raw_frame
