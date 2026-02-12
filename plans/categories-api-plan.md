# Categories API Plan

## Scope
Add budget-scoped category CRUD endpoints for `categories` table fields:
- `id`, `budget_id`, `name`, `parent_id`, `is_archived`, `sort_order`

## Endpoints
- `POST /budgets/{budget_id}/categories`
- `GET /budgets/{budget_id}/categories`
- `GET /budgets/{budget_id}/categories/{category_id}`
- `PATCH /budgets/{budget_id}/categories/{category_id}`
- `DELETE /budgets/{budget_id}/categories/{category_id}`

## Contract
- Request models:
  - `CategoryCreate`: `name`, `parent_id`, `is_archived`, `sort_order`.
  - `CategoryUpdate`: same fields optional.
- Response model:
  - `CategoryResponse` with all table-backed fields.
- Domain model:
  - `Category` dataclass.

## Business Rules
- Names must be unique per budget (`409` on duplicate).
- `parent_id`, when provided:
  - must exist,
  - must belong to the same budget,
  - cannot be self,
  - parent cannot itself have a parent (max depth: one layer),
  - category with children cannot be assigned a parent (max depth: one layer).
- `PATCH` must reject empty payload (`400`) and null fields (`422`) via `extract_updates`.

## File-Level Implementation
- Add `budget_api/models/categories.py`.
- Export new models in `budget_api/models/__init__.py`.
- Add `budget_api/data_access/categories.py` with:
  - `create_category`, `list_categories_by_budget`, `get_category`, `get_category_by_name`, `update_category`, `delete_category`.
- Export store in `budget_api/data_access/__init__.py`.
- Add `budget_api/services/categories.py` with validation and permission-safe lookup behavior.
- Export service in `budget_api/services/__init__.py`.
- Add router `budget_api/routers/categories.py`.
- Mount router in `budget_api/main.py`.
- Optionally add re-export in `budget_api/routers/__init__.py`.

## Test Plan
Add `tests/test_categories.py` with:
- create/list/get/update/delete happy paths,
- list ordering by `sort_order`, `name`, `id`,
- duplicate name conflict,
- invalid or cross-budget `parent_id`,
- parent depth prevention (`parent -> child -> grandchild` disallowed),
- membership and unknown-budget authorization checks,
- transaction integration: deleting a category should leave related lines with `category_id = null` (database FK behavior).

## Acceptance Criteria
- All endpoints work with budget membership checks.
- Unique and hierarchy validations are enforced at service layer before DB errors.
- Category list ordering is deterministic.
