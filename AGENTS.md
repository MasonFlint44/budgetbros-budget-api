# Agent Context: BudgetBros Budget API

## Project overview
- FastAPI service with SQLAlchemy models for a budgeting app.
- Entry point: `budget_api.main:app` (health check at `GET /` returns `{"status": "ok"}`).
- Core schema lives in `budget_api.tables` (users, budgets, accounts, categories, payees, transactions, tags, transfers, splits).

## Layout
- `budget_api/main.py`: FastAPI app definition.
- `budget_api/tables.py`: SQLAlchemy models and schema.
- `tests/`: pytest suite.
- `pyproject.toml`: dependencies and tool config.

## Environment
- Python 3.14+
- Preferred environment manager: `uv`.

## Common commands
```bash
uv sync
uv run fastapi dev budget_api
uv run pytest
```

## Notes for changes
- Migrations and database wiring are not yet set up.
- Transaction amounts are signed integer minor units (cents) in `transaction_lines.amount_minor`.
