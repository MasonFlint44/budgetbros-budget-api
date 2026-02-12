# Tags API Plan

## Scope
Add budget-scoped tag CRUD endpoints for `tags` table fields:
- `id`, `budget_id`, `name`

## Endpoints
- `POST /budgets/{budget_id}/tags`
- `GET /budgets/{budget_id}/tags`
- `GET /budgets/{budget_id}/tags/{tag_id}`
- `PATCH /budgets/{budget_id}/tags/{tag_id}`
- `DELETE /budgets/{budget_id}/tags/{tag_id}`

## Contract
- Request models:
  - `TagCreate`: `name`.
  - `TagUpdate`: optional `name`.
- Response model:
  - `TagResponse` with all table-backed fields.
- Domain model:
  - `Tag` dataclass.

## Business Rules
- Names must be unique per budget (`409` on duplicate).
- Keep transaction tagging nested in transaction line payloads (`tag_ids`); do not add standalone line-tag endpoints.
- `PATCH` uses `extract_updates` for empty/null consistency.
- Deleting a tag should remove entries from `transaction_line_tags` through FK cascade.

## File-Level Implementation
- Add `budget_api/models/tags.py`; export in `budget_api/models/__init__.py`.
- Add `budget_api/data_access/tags.py`; export in `budget_api/data_access/__init__.py`.
- Add `budget_api/services/tags.py`; export in `budget_api/services/__init__.py`.
- Add `budget_api/routers/tags.py`; mount in `budget_api/main.py`.
- Optionally update `budget_api/routers/__init__.py`.

## Test Plan
Add `tests/test_tags.py` with:
- create/list/get/update/delete happy paths,
- duplicate name conflict,
- list ordering by `name`, `id`,
- membership and cross-budget scoping checks,
- null/empty update behavior,
- transaction integration: tag deletion removes line associations and returned `tag_ids` reflect removal.

## Acceptance Criteria
- Tag CRUD is exposed and permissioned.
- Transaction API continues to be the single write path for line-tag links.
