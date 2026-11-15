# Orders Analytics

Orders Analytics is the project scaffold for a technical challenge focused on order data cleaning, SQL reporting, and natural-language SQL generation through a FastAPI endpoint.

This repository is intentionally prepared as a clean and reviewable starting point. The current phase covers project initialization, dependency management, environment configuration, and project structure only. The data-generation and API functionality are defined in the roadmap and will be implemented in subsequent phases.

## Objective

The project must support the following scope once implemented:

- Generate a CSV with at least 1,000 orders containing date, customer, country, product, amount, and status values.
- Clean malformed records before persistence.
- Save processed data in SQLite.
- Expose exactly two SQL views: `sales_by_month_country` for monthly sales by country and `top_customers` for the top 10 customers.
- Provide a FastAPI endpoint that accepts natural-language questions and translates them into validated read-only SQL queries.
- Test the cleaning logic, SQL validation, and LLM-backed endpoint behavior with `pytest` while avoiding real external services.

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

The accepted direction was to keep the repository focused on project preparation and technical setup without implementing the data-generation, cleaning, SQL view, or API logic. A few adjustments were made to ensure the tooling remained compatible with modern Python and `uv`, and to keep the initial repository aligned with the technical challenge requirements instead of overbuilding the architecture.

## Future improvements

The roadmap documents follow-up work for the implementation phase, such as:

- deterministic test data generation,
- robust CSV cleaning and validation,
- SQLite-backed persistence,
- SQL view definitions,
- a validated SQL execution layer,
- LLM integration with prompt and query restrictions,
- and endpoint-level API tests with mocked LLM responses.

These improvements are planned and documented, but not added in this preparation phase.

## Validation

The repository is configured for local validation via:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

This phase is intentionally limited to infrastructure and project readiness checks.
