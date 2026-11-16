"""Read-only SQLite execution helpers with guardrails for approved analytical queries."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

from orders_analytics.config import settings


class SQLExecutionError(RuntimeError):
    """Raised when a read-only query cannot be executed."""

    def __init__(
        self,
        message: str,
        *,
        public_message: str = "The analytical database is unavailable.",
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.public_message = public_message
        self.status_code = status_code


def _database_path_from_url(database_url: str) -> Path:
    """Resolve a SQLite URL into a filesystem path for read-only access."""
    if database_url.startswith("sqlite:///:memory:") or database_url.endswith(":memory:"):
        raise SQLExecutionError(
            "In-memory SQLite databases are not supported for read-only API execution.",
            public_message="Read-only query execution requires a file-backed SQLite database.",
        )

    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise SQLExecutionError(
            f"Unsupported database scheme: {parsed.scheme!r}.",
            public_message="The configured database must use a supported SQLite file URL.",
        )

    path_text = parsed.path
    if path_text in {"", ":memory:"}:
        raise SQLExecutionError(
            "A database file path is required for read-only execution.",
            public_message="The configured SQLite database path is invalid.",
        )

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
        raise SQLExecutionError(
            f"The configured SQLite database does not exist: {path}",
            public_message="The configured SQLite database is unavailable.",
        )
    return path


def execute_read_only_query(query: str, database_url: str | None = None) -> list[dict[str, object]]:
    """Execute a validated read-only query against SQLite in read-only mode."""
    if not query.strip():
        raise SQLExecutionError(
            "The SQL query cannot be empty.",
            public_message="Generated SQL is empty.",
            status_code=422,
        )

    target_url = database_url or settings.DATABASE_URL
    database_path = _database_path_from_url(target_url)
    uri = f"file:{database_path.as_posix()}?mode=ro"
    started_at = time.monotonic()
    row_limit = settings.SQLITE_MAX_RESULT_ROWS

    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.set_progress_handler(
                lambda: int(time.monotonic() - started_at >= settings.SQLITE_QUERY_TIMEOUT_SECONDS),
                1000,
            )
            cursor = connection.execute(query)
            rows = cursor.fetchmany(row_limit + 1)
            if len(rows) > row_limit:
                raise SQLExecutionError(
                    f"The query returned more than the configured row limit of {row_limit}.",
                    public_message=(
                        "The query result exceeds the configured maximum number of rows."
                    ),
                    status_code=422,
                )
    except sqlite3.OperationalError as exc:
        message = str(exc).casefold()
        if "interrupted" in message:
            raise SQLExecutionError(
                "The query exceeded the configured execution time limit.",
                public_message="The analytical query exceeded the execution time limit.",
                status_code=504,
            ) from exc
        if "no such column" in message:
            raise SQLExecutionError(
                f"The generated SQL references an unknown column: {exc}",
                public_message=(
                    "Generated SQL references a column that is not available in the "
                    "approved analytical views."
                ),
                status_code=422,
            ) from exc
        if "syntax error" in message or " near " in message:
            raise SQLExecutionError(
                f"The generated SQL has SQLite syntax errors: {exc}",
                public_message="Generated SQL has SQLite syntax errors.",
                status_code=422,
            ) from exc
        if "attempt to write" in message or "readonly" in message:
            raise SQLExecutionError(
                f"The generated SQL attempted a write operation: {exc}",
                public_message="Generated SQL attempted a write operation, which is not allowed.",
                status_code=422,
            ) from exc
        if "no such table" in message:
            raise SQLExecutionError(
                f"The configured analytical view is unavailable: {exc}",
                public_message=(
                    "The analytical views are unavailable. Load the cleaned data before querying."
                ),
            ) from exc
        raise SQLExecutionError(f"The analytical query could not be executed: {exc}") from exc
    except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
        raise SQLExecutionError(f"The analytical query could not be executed: {exc}") from exc

    return [dict(row) for row in rows]
