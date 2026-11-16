# Orders Analytics

[![CI](https://github.com/iamRio/orders-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/iamRio/orders-analytics/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

I defined the requirements and technical decisions for this order analytics workflow. The implementation covers deterministic data generation and cleaning, SQLite persistence, and analytical views. It also exposes a FastAPI endpoint for validated natural-language queries. This README documents cleaning rules, design decisions, setup, tests, and future production work.

## 1. Data generation, cleaning, and persistence

By default, the generator creates 1,200 base orders with seed 42. It injects duplicate rows and rejects base counts below 1,000. Raw rows also include malformed dates, empty amounts, and empty customer values. Each row contains `date`, `customer`, `country`, `product`, `amount`, and `status`.

The cleaner trims text and lowercases statuses. It accepts ISO (`YYYY-MM-DD`), year-first slash (`YYYY/MM/DD`), day-first (`DD-MM-YYYY`), and US (`MM/DD/YYYY`) dates. It then tries the pandas date-parser fallback and drops unparseable dates or rows with missing required values.

The cleaner parses amounts with `Decimal` and drops empty, non-numeric, or non-finite values. It quantizes valid amounts to two decimal places using `ROUND_HALF_EVEN`. It removes duplicates after normalization, keeps the first occurrence, and stably sorts rows by date.

The source schema has no order identifier, so identical normalized rows count as duplicates. A production feed should add a stable order ID to distinguish legitimate repeated orders. The loader recreates the `orders` table and analytical views on each run.

## 2. SQL models

The loader materializes two analytical views:

| View | Columns | Semantics |
|---|---|---|
| `sales_by_month_country` | `month`, `country`, `total_amount`, `order_count` | Groups all cleaned orders by month (`YYYY-MM`) and country |
| `top_customers` | `customer`, `total_amount`, `order_count` | Ranks customers by total amount and returns at most 10 rows |

SQLite stores normalized amounts as decimal text. The views convert values to integer minor units for aggregation, then return `total_amount` as decimal text. This avoids binary floating-point aggregation and preserves negative adjustments. `top_customers` breaks equal totals by customer name.

## 3. FastAPI natural-language endpoint

`GET /health` returns `{"status":"ok"}`. `POST /query` accepts a JSON `question` from 1 to 2,000 characters. It returns the question, validated SQL, and result rows. The system prompt lists approved view schemas. It asks the model to map categorical filters, including country names, to canonical English values. It also asks the model to map month names to `YYYY-MM` and return one raw SQLite `SELECT`.

A large language model (LLM) generates the SQL but never executes it. SQLGlot parses the statement into an abstract syntax tree (AST). The validator permits one `SELECT` that references only the approved views, `sales_by_month_country` and `top_customers`. It checks common table expressions (CTEs) and subqueries, and rejects base-table access, unauthorized references, multiple statements, and non-`SELECT` statements.

The execution helper opens SQLite in read-only mode with `mode=ro`. The application executes only validated SQL. The prompt supports natural-language questions in Spanish or English.

The API uses these status codes:

| Status | Meaning |
|---|---|
| 422 | Generated SQL is invalid or its result exceeds the row limit |
| 502 | The LLM request failed |
| 503 | SQLite or an analytical view is unavailable |
| 504 | The query exceeded its execution timeout |

Error responses exclude filesystem paths, stack traces, and raw provider messages. The application enforces a 5-second query timeout and a 1,000-row result limit by default. Configure these limits with `SQLITE_QUERY_TIMEOUT_SECONDS` and `SQLITE_MAX_RESULT_ROWS`; oversized results return an error instead of being truncated.

Error responses include `attempted_sql` when the query can be parsed and references only approved views and columns. If the query cannot be shown safely, `attempted_sql` is `null` and `attempted_sql_redacted` is `true`. LLM failures return `null` because the model did not produce SQL.

## 4. Tests and validation

The `pytest` suite covers the required cleaning, SQL validation, and `/query` endpoint behavior with a mocked LLM. It also tests data generation, SQLite loading and views, read-only execution, and API error paths. Tests do not call a real LLM.

Run the tests and code-quality checks with:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## 5. Running the project and project notes

### Install and configure

Use Python 3.12 and `uv`. Install the project and development dependencies:

```bash
uv sync --dev
```

Copy `.env.example` to `.env`. Set `OPENAI_API_KEY` to the credential for your configured endpoint:

```bash
cp .env.example .env
```

In PowerShell, run `Copy-Item .env.example .env`. Do not commit `.env`; `.env.example` contains a placeholder, not a credential. `OPENAI_MODEL` defaults to `gpt-4o-mini`, and `OPENAI_TIMEOUT_SECONDS` defaults to 30. Set `OPENAI_BASE_URL` for an OpenAI-compatible endpoint. `DATABASE_URL` defaults to `sqlite:///./data/database/orders.db`. The query limits are described in the API section.

### Generate, clean, load, and start the API

Run the data scripts in order:

```bash
uv run python scripts/generate_raw_orders.py --rows 1200 --seed 42
uv run python scripts/clean_orders.py \
  --input data/raw/orders_raw.csv \
  --output data/cleaned/orders_clean.csv
uv run python scripts/load_orders_db.py \
  --input data/cleaned/orders_clean.csv \
  --database-url sqlite:///./data/database/orders.db
```

The raw and cleaned CSV files and the SQLite database are generated local artifacts. The scripts recreate them; they are excluded from version control.

Start the API:

```bash
uv run uvicorn orders_analytics.api:app --reload
```

Send a question from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How much did we sell in Spain in March 2024?"}'
```

PowerShell equivalent:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/query -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"¿Cuánto vendimos en España en marzo?"}'
```

### Decisions I made

The decisions below follow the implementation sequence in [ROADMAP.md](ROADMAP.md).

- **Phase 1, runtime and tooling**: I chose Python 3.12 and `uv` for a reproducible local environment and dependency lockfile.
- **Phase 2, data cleaning**: I normalize amounts with `Decimal` and remove exact duplicates after normalization. The input has no order ID, so I would require one before applying business-key deduplication to production data.
- **Phase 3, models and SQL validation**: I expose the two required views, include every cleaned order regardless of status because the challenge defines no status filter, and use SQLGlot AST validation with an exact view allowlist instead of keyword checks.
- **Phase 4, API and LLM integration**: I use the OpenAI SDK with `OPENAI_MODEL` and `OPENAI_API_KEY`; `OPENAI_BASE_URL` is optional. OpenAI-compatible endpoints from services such as OpenAI, OpenRouter, Groq, or Ollama may work if they implement the SDK's Chat Completions contract. The endpoint uses FastAPI's synchronous handler execution for blocking provider and SQLite calls. The project tests the LLM integration with mocks, not against those providers.
- **Phase 4.1, persistence**: I chose file-backed SQLite to avoid external infrastructure. The loader stores normalized amounts as decimal text, and query execution opens SQLite in read-only mode.
- **Phase 5, testing and hardening**: I mock the LLM and test data cleaning, SQL restrictions, endpoint behavior, and error paths without making real provider calls.
- **Phase 6, final review**: I aggregate money as integer minor units, bound SQLite query time and result size, and return categorized API errors without exposing internal filesystem paths, stack traces, or raw provider messages.

### Future improvements

With more time, I would:

- Confirm business rules for status-based totals and add a stable order ID to the source schema.
- Add authentication, rate limiting, structured operational metrics, and broader load testing before exposing the endpoint beyond local development.

## Development process and AI disclosure

I defined the project scope and technical decisions, then reviewed the implementation. I verified the workflow through tests and end-to-end CLI runs. I used an AI coding assistant for implementation support and reviewed its changes before accepting them.

- **What I requested**: Implementation support for the data pipeline, analytical views, SQL validation, FastAPI and LLM integration, focused tests, and technical documentation.
- **What I accepted**: I retained the seeded generator, `Decimal` amount processing, integer-minor-unit view aggregation, and mocked LLM tests after checking them against the requirements.
- **What I corrected or verified**: I verified the view allowlist and nested SQL checks, preserved the tested bilingual prompt, documented exact-row deduplication, checked safe API errors, added query limits, and excluded generated datasets from version control.
