#!/usr/bin/env python3
"""Load the cleaned orders CSV into SQLite and materialize the analytical views."""

from __future__ import annotations

import argparse
from pathlib import Path

from orders_analytics.config import settings
from orders_analytics.database.loader import load_orders_db


def main() -> None:
    """Populate the configured SQLite database from the cleaned order CSV."""
    parser = argparse.ArgumentParser(
        description="Load the cleaned orders CSV into SQLite and create the required views."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/cleaned/orders_clean.csv"),
        help="Input CSV path containing the cleaned order rows.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=settings.database_url,
        help="SQLite database URL to populate.",
    )
    args = parser.parse_args()

    database_path = load_orders_db(input_path=args.input, database_url=args.database_url)
    print(f"Loaded orders into {database_path}")


if __name__ == "__main__":
    main()
