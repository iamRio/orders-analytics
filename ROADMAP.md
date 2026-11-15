# Roadmap

## Phase 1: project preparation

Status: completed.

This phase focuses on establishing the repository, selecting a compatible Python toolchain, configuring environment management, and creating the base project structure.

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

Note: SQLite persistence is intentionally not implemented yet, as required by the challenge scope for this task.

## Phase 3: SQL validation and views

Status: completed.

Completed work:

- define the `sales_by_month_country` view for monthly sales by country,
- define the `top_customers` view for the top 10 customers,
- validate SQL definitions against the project constraints,
- keep the SQL surface limited to read-only operations for the API layer.

The guardrails are implemented in `src/orders_analytics/sql/validation.py` and the view definitions live in `src/orders_analytics/sql/views.py`.

## Phase 4: API and LLM integration

Status: completed.

Completed work:

- build a FastAPI application with a single natural-language query endpoint,
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
- ensure the repository remains deterministic and easy to run locally.

## Phase 6: final review

Status: pending.

Planned work:

- review project quality against the challenge requirements,
- validate that no extra features were added,
- confirm the documentation matches the implemented scope,
- ensure all code, comments, and docs remain in technical English.
