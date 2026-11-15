# Orders Analytics

[![CI](https://github.com/iamRio/orders-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/iamRio/orders-analytics/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Orders Analytics is the project scaffold for a technical challenge focused on order data cleaning, SQL reporting, and natural-language SQL generation through a FastAPI endpoint.

This repository is intentionally prepared as a clean and reviewable starting point. The project includes the deterministic data-generation and CSV-cleaning pipeline, the SQL validation guardrails, the read-only database helper, the LLM boundary, and the FastAPI endpoint that translates natural-language requests into safe, view-scoped SQL. SQLite persistence remains outside the current scope; the API boundary is implemented without allowing write access or direct table queries.

## Objective

The project must support the following scope once implemented:

- Generate a CSV with at least 1,000 orders containing date, customer, country, product, amount, and status values.
- Clean malformed records before persistence.
- Save processed data in SQLite.
- Expose exactly two SQL views: `sales_by_month_country` for monthly sales by country and `top_customers` for the top 10 customers.
- Provide a FastAPI endpoint that accepts natural-language questions and translates them into validated read-only SQL queries.
- Test the cleaning logic, SQL validation, and LLM-backed endpoint behavior with `pytest` while avoiding real external services.

## Current implementation

This repository includes the deterministic raw-data generation module, the cleaning pipeline, the SQL validation layer for the approved analytical views, the read-only database execution helper, the LLM boundary, and the FastAPI endpoint that turns a natural-language question into a validated, read-only SQL query. The utility modules live under `src/orders_analytics/` and are structured around the project rules.

The raw-data pipeline remains available through the CLI entry points:

```bash
uv run python scripts/generate_raw_orders.py --rows 1200 --seed 42
uv run python scripts/clean_orders.py --input data/raw/orders_raw.csv --output data/cleaned/orders_clean.csv
uv run python scripts/load_orders_db.py --input data/cleaned/orders_clean.csv --database-url sqlite:///./data/database/orders.db
```

The generator creates a seed-based dataset with malformed dates, duplicate rows, and blank amounts. The cleaner normalizes date strings, strips whitespace, removes invalid records, drops exact duplicates, and writes a valid CSV. The loader writes the cleaned data to SQLite using normalized decimal text for the `amount` column (for example, `1500.00`), then creates or replaces the `orders` table and the `sales_by_month_country` and `top_customers` views.

The SQL layer defines the `sales_by_month_country` and `top_customers` views and validates that a query is a single read-only `SELECT` restricted to those approved views. The database helper enforces a read-only SQLite URI, the LLM service prepares natural-language prompts for valid SQL generation without allowing direct execution, and the FastAPI endpoint composes the workflow into a single secure request/response path.

## Stack

- Python 3.12
- `uv` for environment and dependency management
- `pandas` for data processing
- `FastAPI` for the REST interface
- `pydantic` and `pydantic-settings` for validation and settings
- `sqlite3` via Python standard library for local persistence
- `sqlglot` for SQL validation and analysis
- `openai` Python SDK for LLM integration
- `pytest` for automated tests
- `ruff` for linting and formatting

## Environment setup

1. Clone the repository.
2. Ensure `uv` is installed and available in the shell.
3. Create the environment and install dependencies:

   ```bash
   uv sync --dev
   ```

4. Activate the virtual environment if required:

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

5. Use environment variables from `.env.example` when needed for the implementation phase.

## Configuration

The project uses:

- `pyproject.toml` for project metadata and tool configuration
- `uv.lock` for reproducible dependency resolution
- `.env.example` as the template for environment variables
- `.gitignore` to keep local development artifacts out of version control

## AI usage during development

This project was prepared under a structured engineering workflow. The AI assistant was asked to:

- assess the technical objective and define the project baseline,
- select a compatible Python and dependency stack,
- create the project scaffold and standard tooling,
- document the scope and the implementation roadmap,
- avoid implementing the business logic before the required phase is reached.

The accepted direction was to keep the repository focused on project preparation and then progressively implement the required data pipeline. A few adjustments were made to ensure the tooling remained compatible with modern Python and `uv`, and to keep the repository aligned with the challenge requirements instead of overbuilding the architecture.

## Future improvements

The roadmap documents follow-up work for the implementation phase, such as:

- deterministic test data generation,
- robust CSV cleaning and validation,
- SQL view definitions,
- a validated read-only SQL execution layer,
- LLM integration with prompt and query restrictions,
- and endpoint-level API tests with mocked LLM responses.

The secure query-preparation pipeline, API contract, and hardening checks are in place, and the remaining work is outside this phase.

## Validation

The repository is configured for local validation via:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

This phase includes the raw-dataset generator, cleaning flow, SQL validation checks, the read-only database helper, the LLM prompt service, the FastAPI endpoint, and the final hardening tests covering empty and disallowed queries, invalid database targets, and loader edge cases.
