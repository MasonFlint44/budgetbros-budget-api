# BudgetBros Budget API

FastAPI backend for a collaborative budgeting app.

The service provides authenticated endpoints for:
- user profile (`/users/me`)
- budgets and budget members
- accounts, categories, payees, tags
- currencies
- transactions (single-line, bulk import, transfer, split, update, delete)

## Tech stack

- Python 3.14+
- FastAPI
- SQLAlchemy async ORM
- PostgreSQL (`asyncpg`)
- Cognito JWT verification (`cognito-jwt-verifier`)
- `uv` for dependency and task management

## Project layout

- `budget_api/main.py`: app setup, lifespan, router registration.
- `budget_api/auth.py`: bearer-token verification and current-user provisioning.
- `budget_api/dependencies.py`: budget member/owner authorization helpers.
- `budget_api/services/`: business logic and validation.
- `budget_api/data_access/`: persistence layer.
- `budget_api/models/`: Pydantic request/response models and domain dataclasses.
- `budget_api/tables.py`: SQLAlchemy ORM schema.
- `budget_api/data/currencies.py`: currency seed data.
- `tests/`: async API tests.

## Environment variables

Set these before importing/running the app or tests:

- `DATABASE_URL`: PostgreSQL connection string.
- `COGNITO_ISSUER`: Cognito issuer URL.
- `COGNITO_CLIENT_IDS`: comma-separated Cognito app client IDs.

Notes:
- `COGNITO_ISSUER` and `COGNITO_CLIENT_IDS` are read at import time by `budget_api/auth.py`.
- `DATABASE_URL` values starting with `postgresql://` or `postgresql+psycopg://` are normalized internally to `postgresql+asyncpg://`.

Example:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/budgetbros"
export COGNITO_ISSUER="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example"
export COGNITO_CLIENT_IDS="exampleclientid123"
```

## Setup

```bash
uv sync
```

## Run the API

```bash
uv run fastapi dev budget_api
```

The API is available at `http://127.0.0.1:8000`.

## Authentication model

- The app uses a global dependency on `get_or_create_current_user`, so API routes require a bearer access token.
- The token must contain:
  - `sub` (UUID format)
  - `email`
- On successful auth, the user row is created if missing and `last_seen_at` is updated.

Quick check (requires a valid token):

```bash
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://127.0.0.1:8000/users/me
```

## API overview

- `GET /`
- `GET /users/me`
- `GET /currencies`
- Budgets:
  - `POST /budgets`
  - `GET /budgets`
  - `PATCH /budgets/{budget_id}`
  - `DELETE /budgets/{budget_id}`
  - `POST /budgets/{budget_id}/members`
  - `GET /budgets/{budget_id}/members`
  - `DELETE /budgets/{budget_id}/members/{user_id}`
- Accounts:
  - `POST /budgets/{budget_id}/accounts`
  - `GET /budgets/{budget_id}/accounts`
  - `PATCH /budgets/{budget_id}/accounts/{account_id}`
  - `DELETE /budgets/{budget_id}/accounts/{account_id}`
- Categories:
  - `POST /budgets/{budget_id}/categories`
  - `GET /budgets/{budget_id}/categories`
  - `GET /budgets/{budget_id}/categories/{category_id}`
  - `PATCH /budgets/{budget_id}/categories/{category_id}`
  - `DELETE /budgets/{budget_id}/categories/{category_id}`
- Payees:
  - `POST /budgets/{budget_id}/payees`
  - `GET /budgets/{budget_id}/payees`
  - `GET /budgets/{budget_id}/payees/{payee_id}`
  - `PATCH /budgets/{budget_id}/payees/{payee_id}`
  - `DELETE /budgets/{budget_id}/payees/{payee_id}`
- Tags:
  - `POST /budgets/{budget_id}/tags`
  - `GET /budgets/{budget_id}/tags`
  - `GET /budgets/{budget_id}/tags/{tag_id}`
  - `PATCH /budgets/{budget_id}/tags/{tag_id}`
  - `DELETE /budgets/{budget_id}/tags/{tag_id}`
- Transactions:
  - `POST /budgets/{budget_id}/transactions`
  - `POST /budgets/{budget_id}/transactions/import`
  - `POST /budgets/{budget_id}/transactions/transfer`
  - `GET /budgets/{budget_id}/transactions`
  - `GET /budgets/{budget_id}/transactions/{transaction_id}`
  - `PATCH /budgets/{budget_id}/transactions/{transaction_id}`
  - `POST /budgets/{budget_id}/transactions/{transaction_id}/split`
  - `DELETE /budgets/{budget_id}/transactions/{transaction_id}`

## Domain behavior highlights

- Currency codes are normalized to uppercase in services.
- Budget/account/category/payee/tag names are unique per budget.
- Transaction amounts are signed minor units (`amount_minor`) and cannot be zero.
- Transfer transactions must net to zero across two distinct accounts.
- `import_id` is unique per budget and treated as immutable after creation.
- Category nesting depth is limited to one parent level.

## Database/schema behavior

- Tables are created at app startup (`Base.metadata.create_all`).
- Currency reference data is seeded/upserted at startup.
- Alembic migrations are not configured yet.
- If you update `budget_api/tables.py`, also update `diagrams/tables.mmd`.

## Run tests

```bash
uv run pytest
```

Useful variants:

```bash
uv run pytest tests/test_users.py
uv run pytest -k transactions
```

Testing notes:
- Tests require a real PostgreSQL database via `DATABASE_URL`.
- Session-scoped setup drops and recreates schema once at test session start.
- Data persists across tests during that session, so tests should avoid assuming empty tables.

## License

MIT. See `LICENSE`.
