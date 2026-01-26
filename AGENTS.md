# AGENTS.md

## Project snapshot
- **Stack**: FastAPI + SQLAlchemy (async) + PostgreSQL.
- **App entrypoint**: `budget_api.main:app` (FastAPI lifespan initializes DB and Cognito keys).
- **Core layers**: routers → services → data_access → tables/models.

## Repo map
- `budget_api/main.py`: FastAPI app, lifespan setup, router registration.
- `budget_api/routers/`: HTTP endpoints (accounts, budgets, currencies).
- `budget_api/services/`: business rules + validation (permission checks, conflict checks).
- `budget_api/data_access/`: DB access with `AsyncSession`.
- `budget_api/tables.py`: SQLAlchemy ORM tables + constraints.
- `budget_api/models.py`: Pydantic request/response schemas + domain dataclasses.
- `budget_api/db.py`: async engine/session lifecycle; uses `DATABASE_URL`.
- `budget_api/auth.py`: Cognito JWT verification; uses `COGNITO_ISSUER` and `COGNITO_CLIENT_IDS`.
- `tests/`: pytest async tests using `httpx` + `asgi_lifespan`.

## Local setup
- Install deps: `uv sync`
- Run API: `uv run fastapi dev budget_api`
- Run tests: `uv run pytest`

## Environment variables
- `DATABASE_URL`: required for runtime and tests (Postgres; asyncpg is used internally).
- `COGNITO_ISSUER`: required for auth in `budget_api/auth.py`.
- `COGNITO_CLIENT_IDS`: comma-separated list for Cognito JWT verification.

## Conventions and behaviors
- **Auth**: All routes use `Depends(get_or_create_current_user)` via app-level dependency. Tests stub token expiry in `tests/conftest.py`.
- **Currency codes**: normalized to uppercase in services; invalid codes return 400.
- **Uniqueness**: budgets, accounts, categories, payees enforce name uniqueness per budget; handle conflicts with 409s.
- **Ordering**: list endpoints generally order by `created_at` (see data_access implementations).
- **Transactions**: amounts are signed minor units (see README note).

## Adding or changing endpoints
- Add routes in `budget_api/routers/`.
- Add validation/permissions in `budget_api/services/`.
- Add DB operations in `budget_api/data_access/`.
- Update/extend schemas in `budget_api/models.py` and tables in `budget_api/tables.py`.
- Add tests in `tests/` using async client fixtures.

## Testing notes
- Tests require a real Postgres DB via `DATABASE_URL`.
- `tests/conftest.py` drops/creates schema per test session and uses `LifespanManager`.

