# Payees API Plan

## Scope
Add budget-scoped payee CRUD endpoints for `payees` table fields:
- `id`, `budget_id`, `name`

## Endpoints
- `POST /budgets/{budget_id}/payees`
- `GET /budgets/{budget_id}/payees`
- `GET /budgets/{budget_id}/payees/{payee_id}`
- `PATCH /budgets/{budget_id}/payees/{payee_id}`
- `DELETE /budgets/{budget_id}/payees/{payee_id}`

## Contract
- Request models:
  - `PayeeCreate`: `name`.
  - `PayeeUpdate`: optional `name`.
- Response model:
  - `PayeeResponse` with all table-backed fields.
- Domain model:
  - `Payee` dataclass.

## Business Rules
- Names must be unique per budget (`409` on duplicate).
- `PATCH` uses `extract_updates` for empty/null behavior consistency.
- Hard delete is allowed; transaction lines should retain row integrity via FK `ON DELETE SET NULL`.

## File-Level Implementation
- Add `budget_api/models/payees.py` and export from `budget_api/models/__init__.py`.
- Add `budget_api/data_access/payees.py` and export from `budget_api/data_access/__init__.py`.
- Add `budget_api/services/payees.py` and export from `budget_api/services/__init__.py`.
- Add `budget_api/routers/payees.py` and mount in `budget_api/main.py`.
- Optionally update `budget_api/routers/__init__.py`.

## Test Plan
Add `tests/test_payees.py` with:
- create/list/get/update/delete happy paths,
- duplicate name conflict,
- list ordering by `name`, `id`,
- membership/scoping and unknown resource checks,
- null/empty update payload behavior,
- transaction integration: deleting payee nulls `transaction_lines.payee_id`.

## Acceptance Criteria
- Full payee CRUD exists under budget routes.
- Name uniqueness and scoping are enforced consistently with accounts/categories behavior.
