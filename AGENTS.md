# AGENTS.md

This repository is the codebase for the **Orders Analytics** technical challenge. Its purpose is to define a modular, well-scoped, and secure architecture that fulfills the challenge requirements without overengineering.

## Core Principles

- **Runtime & Tooling:** Use Python 3.12 as the baseline runtime and `uv` for environment management and dependency locking (`pyproject.toml` and `uv.lock`).
- **Language:** Use technical English for all code, data schemas, comments, commit messages, and documentation (`README.md`, `ROADMAP.md`), while allowing the natural language API endpoint to process user queries in Spanish or English.
- **Modularity & Scope:** Keep modules small with single responsibilities. Strictly separate data generation, CSV cleaning, database persistence, LLM SQL generation, SQL validation, and query execution. Implement only the requirements in the current phase; do not scaffold future phases or add features outside the challenge scope.
- **Type Safety & Precision:** Use strict static type annotations across the codebase. Always use `Decimal` for monetary amounts during processing; store monetary values in SQLite without floating-point rounding errors (e.g., as normalized decimal text or integer minor units) and document the chosen representation.
- **Simplicity:** Avoid premature abstractions, unnecessary design patterns, or redundant package structures.
- **Repository Structure:** Follow the existing project layout and naming conventions. Keep modules focused within the established package structure and place executable scripts under `scripts/`; do not introduce a parallel package layout.

## Data Pipeline Rules

- **Reproducible Dataset:** Generate at least 1,000 raw order rows deterministically (using a fixed seed) with columns `date`, `customer`, `country`, `product`, `amount`, and `status`, intentionally including duplicates, malformed dates, and empty amounts.
- **Deterministic Cleaning:** Define and document explicit rules for deduplication, date normalization, invalid date handling, and missing/invalid monetary amounts so every dropped or normalized row is predictable and traceable.

## Security & SQL Validation Rules

The LLM-to-SQL endpoint must enforce defense-in-depth security:

- **LLM Boundary:** The LLM is strictly limited to generating SQL queries from natural language. It must never execute queries directly.
- **AST-Based Validation:** Every generated SQL query must be parsed and validated structurally using **SQLGlot** before execution. Never rely solely on regular expressions.
- **Read-Only & Whitelist Enforcement:**
  - Allow only a single `SELECT` statement.
  - Reject multiple statements (`;`), unauthorized table/view references inside CTEs or subqueries, and any data-modifying or DDL/administrative commands (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, `PRAGMA`, etc.).
  - Restrict query access exclusively to the authorized analytical views (`sales_by_month_country` and `top_customers`, or their exact configured names); block direct access to base tables.
- **Database Hardening:** Open the SQLite connection in strict read-only mode (`file:...?mode=ro` with `uri=True`) for query execution, alongside additional execution guardrails.
- **Error Handling & Secrets:** Never expose stack traces, internal database schemas, or sensitive configuration in API error responses. Keep all API keys and environment-specific settings in environment variables (`.env` excluded from Git; document keys in `.env.example`).

## Development, Testing & Documentation Standards

- **Code Quality:** Format and lint all code with Ruff (`ruff check .` and `ruff format --check .`) before committing.
- **Documentation:** Use concise docstrings for public modules, classes, and functions when they clarify purpose or behavior. Avoid boilerplate that merely repeats names, signatures, or implementation details.
- **Explicit Failures:** Handle malformed CSV records, LLM failures, and invalid SQL queries with explicit exceptions and clear HTTP error responses—never with silent fallbacks.
- **Behavior-Focused Tests:** Add focused tests for new or changed behavior rather than requiring a test for every module. Provide at least three `pytest` tests covering data cleaning, SQL validation, and the API endpoint with a mocked LLM. Use `HTTPX` for endpoint tests and cover error scenarios such as invalid SQL, LLM failure, and unauthorized table access. Never call a real LLM in tests.
- **Living Documentation:** Follow `ROADMAP.md` task by task, updating `ROADMAP.md` and `README.md` (including setup instructions, technical decisions, future improvements, and the AI usage disclosure detailing what was requested, accepted, and corrected) as features are implemented. Keep commits atomic using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`).

## Dependencies & Repository Hygiene

- Declare runtime and development dependencies in `pyproject.toml` and keep `uv.lock` synchronized with `uv`.
- Do not commit `.env` files, local database files, generated datasets, caches, or debug artifacts. Generate local data through project scripts as needed.
