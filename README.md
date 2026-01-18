# BudgetBros Budget API

FastAPI service and SQLAlchemy models for a budgeting app. The API currently exposes a basic health check and a set of database tables that cover users, shared budgets, accounts, categories, payees, transactions, and tags.

## What is in here

- **FastAPI app**: `budget_api.main:app` with `GET /` returning `{"status": "ok"}`.
- **SQLAlchemy models**: `budget_api.tables` defines the core budgeting schema, including transfers, splits, and tagging.

## Requirements

- Python 3.14+
- `uv` (recommended) or another Python environment manager

## Setup

```bash
uv sync
```

## Run the API

```bash
uv run fastapi dev budget_api
```

The API will be available at `http://127.0.0.1:8000`.

## Run tests

```bash
uv run pytest
```

## Notes

- Database models are defined, but migrations and database wiring are not yet set up.
- Transaction amounts use signed integer minor units (cents) in `transaction_lines.amount_minor`.

## License

MIT. See `LICENSE`.
