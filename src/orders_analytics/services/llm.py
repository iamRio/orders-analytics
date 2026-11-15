"""LLM service for translating natural-language questions into SQL."""

from __future__ import annotations

import re

from openai import OpenAI

from orders_analytics.config import Settings


class LLMServiceError(RuntimeError):
    """Raised when the LLM cannot create a valid SQL query."""


class LLMService:
    """Translate a natural-language question into approved read-only SQL."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_sql(self, question: str) -> str:
        """Use the configured LLM to produce read-only SQL for a view."""
        if not self.settings.OPENAI_API_KEY:
            raise LLMServiceError(
                "OPENAI_API_KEY is not configured and the LLM cannot generate SQL."
            )

        prompt = (
            "You are a SQL generator for a SQLite data warehouse. "
            "Return only one SQL SELECT statement. "
            "The query must read from exactly one of these views: "
            "sales_by_month_country or top_customers. "
            "Do not use DDL, DML, or any table other than the approved views.\n\n"
            f"Question: {question}"
        )

        client = OpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            timeout=self.settings.OPENAI_TIMEOUT_SECONDS,
        )

        try:
            response = client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": "Generate only SQLite SQL SELECT statements."},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - exercise through unit tests with a stub
            raise LLMServiceError(f"The LLM request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMServiceError("The LLM response did not include SQL content.")

        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
