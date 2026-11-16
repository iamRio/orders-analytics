"""Tests for prompt construction in the LLM SQL generation service."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from orders_analytics.config import Settings
from orders_analytics.services.llm import LLMService, LLMServiceError


def test_llm_prompt_preserves_bilingual_semantic_mapping(monkeypatch) -> None:
    """The prompt must preserve its semantic mapping instructions and pass the question."""
    expected_sql = (
        "SELECT month, total_amount FROM sales_by_month_country "
        "WHERE country = 'Spain' AND month = '2024-03'"
    )
    question = "¿Cuánto vendimos en España en marzo de 2024?"

    class FakeCompletions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            messages = kwargs["messages"]
            assert isinstance(messages, list)
            system_prompt = messages[0]["content"]
            user_prompt = messages[1]["content"]
            assert isinstance(system_prompt, str)
            assert isinstance(user_prompt, str)
            assert "`month` [format: YYYY-MM string or YYYY-MM-DD]" in system_prompt
            assert "`country` [canonical English names, abbr or codes]" in system_prompt
            assert (
                "`top_customers` (Columns: `customer`, `total_amount`, `order_count`)"
                in system_prompt
            )
            assert "canonical English values" in system_prompt
            assert "Spanish countries or month names" in system_prompt
            assert "YYYY-MM" in system_prompt
            assert "Return only raw SQL as plain text" in system_prompt
            assert "without markdown blocks, quotes, or explanations" in system_prompt
            assert "No DDL or DML" in system_prompt
            assert user_prompt == question
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=expected_sql))]
            )

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str | None, timeout: int) -> None:
            assert api_key == "test-key"
            assert base_url is None
            assert timeout > 0
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("orders_analytics.services.llm.OpenAI", FakeOpenAI)

    service = LLMService(
        Settings(OPENAI_API_KEY="test-key", OPENAI_BASE_URL=None, OPENAI_TIMEOUT_SECONDS=5)
    )
    assert service.generate_sql(question) == expected_sql


def test_llm_client_construction_failure_is_classified_without_provider_details(
    monkeypatch,
) -> None:
    """Client setup errors should be converted to a safe, descriptive service error."""

    class BrokenOpenAI:
        def __init__(self, *, api_key: str, base_url: str | None, timeout: int) -> None:
            raise RuntimeError("provider's private response included secret configuration")

    monkeypatch.setattr("orders_analytics.services.llm.OpenAI", BrokenOpenAI)
    service = LLMService(
        Settings(OPENAI_API_KEY="test-key", OPENAI_BASE_URL=None, OPENAI_TIMEOUT_SECONDS=5)
    )

    with pytest.raises(LLMServiceError) as error:
        service.generate_sql("Show sales")

    assert "RuntimeError" in str(error.value)
    assert "provider's private response" not in str(error.value)
    assert "secret configuration" not in str(error.value)
