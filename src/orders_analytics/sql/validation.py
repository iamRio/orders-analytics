"""Guardrails for authorizing read-only analytical queries against the approved views."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ALLOWED_ANALYTICAL_VIEWS: tuple[str, ...] = ("sales_by_month_country", "top_customers")


class SQLValidationError(ValueError):
    """Raised when a user query is not allowed by the SQL guardrails."""


def _strip_trailing_semicolon(text: str) -> str:
    """Remove a single terminal semicolon while preserving query content."""
    candidate = text.strip()
    if candidate.endswith(";"):
        return candidate[:-1].rstrip()
    return candidate


def _extract_table_names(expression: exp.Expression) -> set[str]:
    """Collect table references from the parsed SELECT expression."""
    return {
        node.name.lower()
        for node in expression.find_all(exp.Table)
        if node.name and node.name.lower() not in {"cte", "*"}
    }


def validate_sql_query(
    query: str,
    allowed_views: Sequence[str] | Iterable[str] = ALLOWED_ANALYTICAL_VIEWS,
) -> str:
    """Validate that the query is a single read-only SELECT against an approved analytical view."""
    candidate = query.strip()
    if not candidate:
        raise SQLValidationError("The SQL query cannot be empty.")

    candidate = _strip_trailing_semicolon(candidate)
    if ";" in candidate:
        raise SQLValidationError("Only a single SELECT statement is allowed.")

    try:
        parsed = sqlglot.parse_one(candidate, read="sqlite")
    except ParseError as exc:
        raise SQLValidationError(f"The SQL query is invalid: {exc}") from exc

    if not isinstance(parsed, exp.Select):
        raise SQLValidationError("Only SELECT statements are permitted.")

    table_names = _extract_table_names(parsed)
    if not table_names:
        raise SQLValidationError("The query must reference an approved analytical view.")

    allowed_names = {name.lower() for name in allowed_views}
    unauthorized = sorted(table_names - allowed_names)
    if unauthorized:
        unauthorized_list = ", ".join(unauthorized)
        raise SQLValidationError(
            "The query references unauthorized tables or views: "
            f"{unauthorized_list}. Only {', '.join(sorted(allowed_names))} are allowed."
        )

    return parsed.sql(dialect="sqlite")
