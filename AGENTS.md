# AGENTS.md

## Purpose
Guide for AI coding agents working in this repository. Use this file to make changes that match existing architecture, behavior, and test style.

## Project snapshot
- Stack: FastAPI + SQLAlchemy async ORM + PostgreSQL (`asyncpg`) + Cognito JWT auth.
- Entrypoint: `budget_api.main:app`.
- Layering: routers -> services -> data_access -> tables/models.
- Runtime DB setup: app lifespan calls `db.init_db()` (`create_all`) and seeds currencies.

## Important runtime/env behavior
- `budget_api/auth.py` reads `COGNITO_ISSUER` and `COGNITO_CLIENT_IDS` at import time via `os.environ[...]`.
- Missing auth env vars fail early during import, even in tests.
- `DATABASE_URL` is required for runtime and tests; `db.py` normalizes
  - `postgresql://...` -> `postgresql+asyncpg://...`
  - `postgresql+psycopg://...` -> `postgresql+asyncpg://...`

## Local setup
- Install dependencies: `uv sync`
- Run API: `uv run fastapi dev budget_api`
- Run tests: `uv run pytest`

## Repo map (current)
- `budget_api/main.py`: app config, lifespan, router registration.
- `budget_api/auth.py`: OAuth2 bearer setup and `get_or_create_current_user`.
- `budget_api/dependencies.py`: budget membership/ownership guards.
- `budget_api/db.py`: async engine/session lifecycle helpers.
- `budget_api/tables.py`: ORM schema and constraints.
- `budget_api/models/`: request/response models + domain dataclasses (split by domain).
- `budget_api/routers/`: HTTP surface.
- `budget_api/services/`: business logic and validation.
- `budget_api/data_access/`: DB reads/writes mapped to domain dataclasses.
- `budget_api/data/currencies.py`: seed currency rows.
- `tests/`: async API and service behavior tests.
- `diagrams/tables.mmd`: Mermaid schema diagram (must track `tables.py`).

## API surface (high-level)
- `GET /` health check.
- `GET /users/me`.
- `GET /currencies`.
- `POST /budgets`, `GET /budgets`, `PATCH /budgets/{budget_id}`, `DELETE /budgets/{budget_id}`.
- `POST /budgets/{budget_id}/members`, `GET /budgets/{budget_id}/members`, `DELETE /budgets/{budget_id}/members/{user_id}`.
- Accounts: `POST /budgets/{budget_id}/accounts`, `GET /budgets/{budget_id}/accounts`, `PATCH /budgets/{budget_id}/accounts/{account_id}`, `DELETE /budgets/{budget_id}/accounts/{account_id}`.
- Categories: `POST /budgets/{budget_id}/categories`, `GET /budgets/{budget_id}/categories`, `GET /budgets/{budget_id}/categories/{category_id}`, `PATCH /budgets/{budget_id}/categories/{category_id}`, `DELETE /budgets/{budget_id}/categories/{category_id}`.
- Payees: `POST /budgets/{budget_id}/payees`, `GET /budgets/{budget_id}/payees`, `GET /budgets/{budget_id}/payees/{payee_id}`, `PATCH /budgets/{budget_id}/payees/{payee_id}`, `DELETE /budgets/{budget_id}/payees/{payee_id}`.
- Tags: `POST /budgets/{budget_id}/tags`, `GET /budgets/{budget_id}/tags`, `GET /budgets/{budget_id}/tags/{tag_id}`, `PATCH /budgets/{budget_id}/tags/{tag_id}`, `DELETE /budgets/{budget_id}/tags/{tag_id}`.
- Transactions:
  - `POST /budgets/{budget_id}/transactions`
  - `POST /budgets/{budget_id}/transactions/import`
  - `POST /budgets/{budget_id}/transactions/transfer`
  - `GET /budgets/{budget_id}/transactions`
  - `GET /budgets/{budget_id}/transactions/{transaction_id}`
  - `PATCH /budgets/{budget_id}/transactions/{transaction_id}`
  - `POST /budgets/{budget_id}/transactions/{transaction_id}/split`
  - `DELETE /budgets/{budget_id}/transactions/{transaction_id}`

## Architectural conventions
- Routers stay thin: parse params, enforce dependency guard, delegate to service.
- Services own business rules and raise `HTTPException` with stable detail messages.
- Data access layer performs persistence and returns domain dataclasses.
- `models/*` generally define:
  - Pydantic `*Create/*Update/*Response`
  - frozen dataclass domain models used between service and data_access.
- Patch-style updates usually use `budget_api/routers/utils.py::extract_updates`:
  - empty payload -> `400` ("No fields to update.")
  - explicit `null` in update fields -> `422`.
- Budget-scoped authorization uses:
  - `require_budget_member(...)` for operations available to any budget member.
  - `require_budget_owner(...)` for owner-only operations (delete budget, manage members).

## Domain invariants agents must preserve
- Auth/user:
  - App-level dependency enforces authentication globally.
  - Current user is created on first authenticated request and `last_seen_at` is updated.
- Currency:
  - Codes are normalized to uppercase in services.
  - Budget/account currency mismatches are rejected.
- Uniqueness/conflicts:
  - Name uniqueness is per budget for accounts/categories/payees/tags.
  - Conflict responses are `409`.
- Categories:
  - Max depth is one level (parent cannot itself have a parent).
  - Category cannot be its own parent.
- Transactions:
  - Amounts are signed minor units and cannot be zero.
  - Allowed statuses: `pending`, `posted`, `reconciled`, `void` (normalized lowercase).
  - Naive datetimes are treated as UTC; stored/returned as timezone-aware.
  - Transfer rules: two distinct accounts, no category, sum of line amounts must be zero.
  - Non-transfer rule: all lines must belong to one account.
  - `import_id` is unique per budget and immutable after creation.
  - Tag IDs are deduplicated; response line `tag_ids` are sorted by `tag_id`.
- Ordering:
  - Budgets/accounts by `created_at` ascending.
  - Categories by `sort_order`, then `name`, then `id`.
  - Payees/tags by `name`, then `id`.
  - Transactions by `posted_at` desc, then `created_at` desc, then `id` desc.

## Making changes safely
When adding/changing an endpoint, update all relevant layers:
1. Router (`budget_api/routers/*.py`) for request/response and dependency wiring.
2. Service (`budget_api/services/*.py`) for validation, permission-aware behavior, and HTTP errors.
3. Data access (`budget_api/data_access/*.py`) for SQLAlchemy operations.
4. Models (`budget_api/models/*.py`) for payload/response/domain types.
5. Tables (`budget_api/tables.py`) only when schema changes are needed.
6. Tests (`tests/`) for success path, validation, auth/permission, and regression coverage.
7. Diagram (`diagrams/tables.mmd`) whenever `budget_api/tables.py` changes.

## Testing notes
- Tests are async and use `httpx.AsyncClient` + `LifespanManager`.
- `tests/conftest.py` drops and recreates schema once per test session.
- Test data persists across tests within that session. Avoid assumptions that tables start empty.
- Prefer unique names/IDs in tests (`uuid4()` helpers are common).
- `override_verifier_expiry` fixture allows expired test token by monkey-patching verifier behavior.

## Recommended agent workflow
1. Read the router + service + data_access file for the domain being changed.
2. Reuse existing error strings/status semantics to avoid breaking tests/clients.
3. Add/adjust tests in the corresponding `tests/test_*.py`.
4. Run focused tests first, then broader suite if time permits.
5. If schema changed, update `diagrams/tables.mmd`.

## Quick commands
- Full tests: `uv run pytest`
- Single file: `uv run pytest tests/test_transactions.py`
- Filtered tests: `uv run pytest -k "transactions and split"`
