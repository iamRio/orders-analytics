"""LLM service for translating natural-language questions into SQL."""

from __future__ import annotations

import logging
import re

from openai import OpenAI

from orders_analytics.config import Settings

logger = logging.getLogger(__name__)


class LLMServiceError(RuntimeError):
    """Raised when the LLM cannot create a valid SQL query."""


SYSTEM_PROMPT = (
    "You are a robust and strict SQL generator for a SQLite data warehouse. "
    "Translate the natural language question into one valid SQLite SELECT statement.\n\n"
    "You must follow these constraints strictly:\n\n"
    "1. **Approved Views & Schema**: You can ONLY read from:\n"
    "   - `sales_by_month_country` (Columns: `month` [format: YYYY-MM string or YYYY-MM-DD], "
    "`country` [canonical English names, abbr or codes], `total_amount`, `order_count`)\n"
    "   - `top_customers` (Columns: `customer`, `total_amount`, `order_count`)\n"
    "2. **Format & Safety**: Return only raw SQL as plain text, without markdown blocks, "
    "quotes, or explanations. No DDL or DML.\n"
    "3. **Semantic Mapping**: Automatically translate user terminology, local entities, "
    "and languages such as Spanish countries or month names to their corresponding "
    "canonical English values and standard `YYYY-MM` formats present in the data views.\n"
    "4. **Column Integrity**: Use only the columns listed above; never invent tables "
    "or columns.\n\n"
)


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

        try:
            client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                base_url=self.settings.OPENAI_BASE_URL,
                timeout=self.settings.OPENAI_TIMEOUT_SECONDS,
            )
            response = client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            )
        except Exception as exc:  # pragma: no cover - exercise through unit tests with a stub
            logger.exception("LLM SQL generation request failed.")
            raise LLMServiceError(
                f"The LLM provider request failed ({type(exc).__name__}). "
                "Check provider availability and configuration."
            ) from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMServiceError(
                "The LLM provider returned an invalid completion response."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMServiceError("The LLM provider returned an empty SQL response.")

        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
