"""Request and response schemas for the SQL query endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Natural-language question submitted to the SQL generator."""

    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    """Response payload with the validated SQL and the result rows."""

    question: str
    sql: str
    rows: list[dict[str, Any]]
