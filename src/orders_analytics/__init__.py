"""Project root for the Orders Analytics technical challenge."""

from __future__ import annotations

from orders_analytics.api import app, create_app


def main() -> None:
    """Placeholder CLI entry point for the repository scaffold."""
    print(
        "Orders Analytics is initialized. "
        "The data pipeline and API are available in the current implementation."
    )


__all__ = ["app", "create_app", "main"]
