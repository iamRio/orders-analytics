# Roadmap

## Phase 1: project preparation

Status: completed.

This phase establishes the repository, Python toolchain, environment management, and base project structure.

Completed tasks:

- verify the available environment and toolchain,
- install `uv` and a stable Python 3.12 runtime,
- initialize the repository and Python virtual environment,
- configure `pyproject.toml` for dependencies and project metadata,
- generate `uv.lock` for reproducible installs,
- configure `pytest` and `ruff`,
- create the project directory structure,
- define repository instructions in `AGENTS.md`,
- document the project intent in `README.md`.

## Phase 2: data pipeline

Status: completed for the raw-data generation and CSV cleaning stage.

Completed work:

- create a deterministic dataset generator for 1,000+ orders,
- include malformed rows deliberately to test cleaning behavior,
- implement CSV cleaning logic for dates, blank amounts, and duplicate rows,
- verify data integrity before the later persistence phase,
- document the CLI usage for generation and cleaning.

SQLite persistence is implemented in Phase 4.1.

## Phase 3: SQL validation and views

Status: completed.

Completed work:

- define the `sales_by_month_country` view for monthly sales by country,
- define the `top_customers` view for the top 10 customers,
- validate SQL definitions against the project constraints,
- keep the SQL surface limited to read-only operations for the API layer.

SQL guardrails live in `src/orders_analytics/sql/validation.py`. View definitions live in `src/orders_analytics/sql/views.py`.

## Phase 4: API and LLM integration

Status: completed.

Completed work:

- build a FastAPI application with a natural-language query endpoint and a liveness route,
- generate SQL via an LLM service while keeping the LLM at the boundary and never executing SQL directly,
- validate SQL before execution using SQLGlot-based guardrails,
- restrict access to the approved analytical views only,
- return explicit HTTP errors for LLM failures, invalid SQL, and unauthorized access,
- keep the interface focused on read-only operations.

## Phase 4.1: SQLite persistence and view materialization

Status: completed.

Completed work:

- add a SQLite loader that reads the cleaned CSV into the configured database,
- create or replace the `orders` table with normalized decimal-text amounts,
- create or replace the `sales_by_month_country` and `top_customers` views from the approved SQL definitions,
- validate the persisted data through the read-only execution helper.

## Phase 5: automated tests and hardening

Status: completed.

Completed work:

- add `pytest` coverage for data cleaning,
- validate query restrictions and SQL safety checks,
- test the endpoint with a mocked LLM response,
- verify edge cases for invalid queries and failure paths,
- harden the SQLite execution and loader paths against memory databases and invalid empty queries,
- bound SQLite query execution time and returned row counts,
- ensure the repository remains deterministic and straightforward to run locally.

## Phase 6: final review

Status: completed.

Completed work:

- review project quality against the challenge requirements,
- verify that no out-of-scope business features were added and that `/health` remains a liveness check,
- confirm the documentation matches the implemented scope,
- ensure all code, comments, and docs remain in technical English,
- use integer minor units when aggregating normalized decimal-text amounts in analytical views,
- prevent API error responses from exposing raw provider messages or internal database paths.
