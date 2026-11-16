"""FastAPI application for secure natural-language SQL queries."""

from __future__ import annotations

import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from orders_analytics.config import settings
from orders_analytics.database.connection import SQLExecutionError, execute_read_only_query
from orders_analytics.schemas.query import QueryRequest, QueryResponse
from orders_analytics.services.llm import LLMService, LLMServiceError
from orders_analytics.sql.validation import (
    SQLValidationError,
    safe_sql_preview,
    validate_sql_query,
)

logger = logging.getLogger(__name__)


def _query_error_response(
    status_code: int,
    detail: str,
    attempted_sql: str | None = None,
) -> JSONResponse:
    safe_preview = safe_sql_preview(attempted_sql) if attempted_sql is not None else None
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "attempted_sql": safe_preview,
            "attempted_sql_redacted": attempted_sql is not None and safe_preview is None,
        },
    )


def create_app() -> FastAPI:
    """Create the application instance for the analytical query API."""
    application = FastAPI(
        title="Orders Analytics",
        version="0.1.0",
        description="Translate a natural-language request into a validated read-only SQL query.",
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        """Return a simple liveness response for the API service."""
        return {"status": "ok"}

    @application.post("/query", response_model=QueryResponse)
    def query_orders(payload: QueryRequest) -> QueryResponse | JSONResponse:
        """Generate, validate, and execute a safe analytical query from natural language."""
        llm_service = LLMService(settings)

        try:
            sql = llm_service.generate_sql(payload.question)
        except LLMServiceError as exc:
            logger.warning("SQL generation failed: %s", exc)
            return _query_error_response(
                status.HTTP_502_BAD_GATEWAY,
                f"LLM SQL generation failed: {exc}",
            )

        try:
            validated_sql = validate_sql_query(sql)
        except SQLValidationError as exc:
            return _query_error_response(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                str(exc),
                attempted_sql=sql,
            )

        try:
            rows = execute_read_only_query(validated_sql)
        except SQLExecutionError as exc:
            logger.exception("Read-only analytical query execution failed.")
            return _query_error_response(
                exc.status_code,
                exc.public_message,
                attempted_sql=validated_sql,
            )

        return QueryResponse(
            question=payload.question,
            sql=validated_sql,
            rows=rows,
        )

    return application


app = create_app()
