"""FastAPI application for secure natural-language SQL queries."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, status

from orders_analytics.config import settings
from orders_analytics.database.connection import SQLExecutionError, execute_read_only_query
from orders_analytics.schemas.query import QueryRequest, QueryResponse
from orders_analytics.services.llm import LLMService, LLMServiceError
from orders_analytics.sql.validation import SQLValidationError, validate_sql_query

logger = logging.getLogger(__name__)


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
    async def query_orders(payload: QueryRequest) -> QueryResponse:
        """Generate, validate, and execute a safe analytical query from natural language."""
        llm_service = LLMService(settings)

        try:
            sql = llm_service.generate_sql(payload.question)
        except LLMServiceError as exc:
            logger.warning("SQL generation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The SQL generation service could not process the request.",
            ) from exc

        try:
            validated_sql = validate_sql_query(sql)
        except SQLValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        try:
            rows = execute_read_only_query(validated_sql)
        except SQLExecutionError as exc:
            logger.exception("Read-only analytical query execution failed.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The analytical query could not be completed.",
            ) from exc

        return QueryResponse(
            question=payload.question,
            sql=validated_sql,
            rows=rows,
        )

    return application


app = create_app()
