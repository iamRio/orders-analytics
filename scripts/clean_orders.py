#!/usr/bin/env python3
"""Clean the raw order dataset and write a normalized CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path

from orders_analytics.data.cleaning import clean_orders_csv


def main() -> None:
    """Command-line interface to clean the raw CSV dataset."""
    parser = argparse.ArgumentParser(
        description="Clean the raw order CSV and keep only valid records."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/orders_raw.csv"),
        help="Input CSV file path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cleaned/orders_clean.csv"),
        help="Destination CSV path.",
    )
    args = parser.parse_args()

    dataframe = clean_orders_csv(
        input_path=args.input,
        output_path=args.output,
    )
    print(f"Saved {len(dataframe)} cleaned rows to {args.output}")


if __name__ == "__main__":
    main()
