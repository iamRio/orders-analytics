"""Read-only SQLite execution helpers with guardrails for approved analytical queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from orders_analytics.config import settings


class SQLExecutionError(RuntimeError):
    """Raised when a read-only query cannot be executed."""


def _database_path_from_url(database_url: str) -> Path:
    """Resolve a SQLite URL into a filesystem path for read-only access."""
    if database_url.startswith("sqlite:///:memory:") or database_url.endswith(":memory:"):
        raise SQLExecutionError(
            "In-memory SQLite databases are not supported for read-only API execution."
        )

    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise SQLExecutionError(f"Unsupported database scheme: {parsed.scheme!r}.")

    path_text = parsed.path
    if path_text in {"", ":memory:"}:
        raise SQLExecutionError("A database file path is required for read-only execution.")

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

    path = Path(path_text)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    if not path.exists():
        raise SQLExecutionError(f"The configured SQLite database does not exist: {path}")
    return path


def execute_read_only_query(query: str, database_url: str | None = None) -> list[dict[str, object]]:
    """Execute a validated read-only query against SQLite in read-only mode."""
    if not query.strip():
        raise SQLExecutionError("The SQL query cannot be empty.")

    target_url = database_url or settings.DATABASE_URL
    database_path = _database_path_from_url(target_url)
    uri = f"file:{database_path.as_posix()}?mode=ro"

    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(query)
            rows = cursor.fetchall()
    except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
        raise SQLExecutionError(f"The query could not be executed: {exc}") from exc

    return [dict(row) for row in rows]
