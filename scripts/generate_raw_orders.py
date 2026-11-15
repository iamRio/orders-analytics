#!/usr/bin/env python3
"""Generate a deterministic raw order dataset for the challenge."""

from __future__ import annotations

import argparse
from pathlib import Path

from orders_analytics.data.generation import generate_raw_orders_csv


def main() -> None:
    """Command-line interface to create the raw CSV of orders."""
    parser = argparse.ArgumentParser(
        description="Generate the raw CSV dataset for Orders Analytics."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/orders_raw.csv"),
        help="Destination CSV path.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=1200,
        help="Number of raw order rows to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic seed for reproducible data generation.",
    )
    args = parser.parse_args()

    dataframe = generate_raw_orders_csv(
        output_path=args.output,
        row_count=args.rows,
        seed=args.seed,
    )
    print(f"Generated {len(dataframe)} raw rows at {args.output}")


if __name__ == "__main__":
    main()
