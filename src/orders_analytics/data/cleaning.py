"""Cleaning rules for raw order records before they are persisted later in the pipeline."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from orders_analytics.data.generation import ORDER_COLUMNS


def _normalize_status(value: object) -> str:
    """Normalize status labels to a lower-case, trimmed string."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _normalize_customer(value: object) -> str:
    """Trim whitespace while preserving the original casing for the customer field."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_country(value: object) -> str:
    """Trim whitespace for the country field."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_product(value: object) -> str:
    """Trim whitespace for the product field."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_date(value: object) -> str:
    """Normalize known date formats to ISO format and reject malformed values."""
    if value is None or pd.isna(value):
        return ""

    date_text = str(value).strip()
    if not date_text:
        return ""

    for date_format in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            parsed = pd.to_datetime(date_text, format=date_format, errors="raise")
            return parsed.strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            continue

    try:
        parsed = pd.to_datetime(date_text, errors="raise")
        return parsed.strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def _parse_amount(value: object) -> Decimal | None:
    """Parse a monetary value and reject empty or invalid numbers."""
    if value is None or pd.isna(value):
        return None

    candidate = str(value).strip()
    if candidate == "":
        return None

    try:
        parsed = Decimal(candidate)
    except InvalidOperation:
        return None

    if parsed.is_nan() or parsed.is_infinite():
        return None

    return parsed.quantize(Decimal("0.01"))


def clean_orders_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic cleaning rules to a raw order DataFrame."""
    if frame.empty:
        return pd.DataFrame(columns=ORDER_COLUMNS)

    required_columns = set(ORDER_COLUMNS)
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"The input DataFrame is missing required columns: {missing}")

    normalized = frame.copy()
    normalized = normalized.loc[:, ORDER_COLUMNS].copy()

    for column in ["date", "customer", "country", "product", "amount", "status"]:
        normalized[column] = normalized[column].map(
            lambda value: str(value).strip() if not pd.isna(value) else ""
        )

    normalized["date"] = normalized["date"].map(_normalize_date)
    normalized["customer"] = normalized["customer"].map(_normalize_customer)
    normalized["country"] = normalized["country"].map(_normalize_country)
    normalized["product"] = normalized["product"].map(_normalize_product)
    normalized["status"] = normalized["status"].map(_normalize_status)
    normalized["amount"] = normalized["amount"].map(_parse_amount)

    normalized = normalized[
        normalized["date"].ne("")
        & normalized["customer"].ne("")
        & normalized["country"].ne("")
        & normalized["product"].ne("")
        & normalized["status"].ne("")
        & normalized["amount"].notna()
    ].copy()

    normalized["amount"] = normalized["amount"].map(lambda value: str(value))
    normalized = normalized.drop_duplicates(ignore_index=True)
    normalized = normalized.sort_values("date", kind="mergesort").reset_index(drop=True)
    normalized = normalized.loc[:, ORDER_COLUMNS]
    return normalized


def clean_orders_csv(
    input_path: str | Path = Path("data/raw/orders_raw.csv"),
    output_path: str | Path = Path("data/cleaned/orders_clean.csv"),
) -> pd.DataFrame:
    """Read a raw CSV file, clean it, and persist the cleaned result."""
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"The source CSV does not exist: {input_file}")

    raw_frame = pd.read_csv(input_file)
    cleaned = clean_orders_frame(raw_frame)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_file, index=False)
    return cleaned
