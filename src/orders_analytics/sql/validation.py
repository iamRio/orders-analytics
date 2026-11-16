"""Guardrails for authorizing read-only analytical queries against the approved views."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from sqlglot.optimizer.scope import Scope, traverse_scope

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
    """Collect physical table references while excluding resolved CTE sources."""
    return {
        table.name.lower()
        for scope in traverse_scope(expression)
        for table in scope.tables
        if table.name
        and (table.db or table.catalog or not isinstance(scope.sources.get(table.name), Scope))
    }


def safe_sql_preview(
    query: str,
    allowed_views: Sequence[str] | Iterable[str] = ALLOWED_ANALYTICAL_VIEWS,
) -> str | None:
    """Return a parsed query preview only when it cannot expose unapproved schema."""
    candidate = _strip_trailing_semicolon(query.strip())
    if not candidate or ";" in candidate:
        return None

    try:
        parsed = sqlglot.parse_one(candidate, read="sqlite")
    except ParseError:
        return None

    if not isinstance(parsed, exp.Query):
        return None

    allowed_names = {name.lower() for name in allowed_views}
    table_names = _extract_table_names(parsed)
    if not table_names or table_names - allowed_names:
        return None

    if any(table.db or table.catalog for table in parsed.find_all(exp.Table)):
        return None

    allowed_columns = {
        "month",
        "country",
        "total_amount",
        "order_count",
        "customer",
    }
    if any(
        column.name != "*" and column.name.lower() not in allowed_columns
        for column in parsed.find_all(exp.Column)
    ):
        return None

    return parsed.sql(dialect="sqlite")


def validate_sql_query(
    query: str,
    allowed_views: Sequence[str] | Iterable[str] = ALLOWED_ANALYTICAL_VIEWS,
) -> str:
    """Validate that the query is a single read-only SELECT against an approved analytical view."""
    candidate = query.strip()
    if not candidate:
        raise SQLValidationError("Generated SQL is empty.")

    candidate = _strip_trailing_semicolon(candidate)
    if ";" in candidate:
        raise SQLValidationError(
            "Security policy violation: only a single SQL statement is allowed."
        )

    try:
        parsed = sqlglot.parse_one(candidate, read="sqlite")
    except ParseError as exc:
        errors = exc.errors
        description = errors[0].get("description") if errors else None
        reason = description or "the SQL parser rejected the statement"
        raise SQLValidationError(f"Generated SQL has invalid syntax: {reason}.") from exc

    if not isinstance(parsed, exp.Select):
        raise SQLValidationError("Security policy violation: only SELECT statements are allowed.")

    table_names = _extract_table_names(parsed)
    if not table_names:
        raise SQLValidationError("Generated SQL must reference an approved analytical view.")

    allowed_names = {name.lower() for name in allowed_views}
    unauthorized = sorted(table_names - allowed_names)
    if unauthorized:
        unauthorized_list = ", ".join(unauthorized)
        raise SQLValidationError(
            "Security policy violation: unauthorized tables or views referenced: "
            f"{unauthorized_list}. Only {', '.join(sorted(allowed_names))} are allowed."
        )

    return parsed.sql(dialect="sqlite")
