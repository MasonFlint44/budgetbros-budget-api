# API Surface Roadmap (Table-Driven)

## Goal
Complete the table-backed API surface that is not yet exposed by routers.

## Coverage Matrix
| Table | Status | Existing API Surface | Plan |
|---|---|---|---|
| `currencies` | Implemented | `GET /currencies` | Keep read-only |
| `users` | Partial | auth dependency creates/updates current user | Add `GET /users/me` (`plans/users-api-plan.md`) |
| `budgets` | Implemented | create/list/update/delete | No change |
| `budget_members` | Implemented | add/remove/list members under budgets | No change |
| `accounts` | Implemented | create/list/update/delete under budgets | No change |
| `categories` | Missing | none | Add CRUD under budgets (`plans/categories-api-plan.md`) |
| `payees` | Missing | none | Add CRUD under budgets (`plans/payees-api-plan.md`) |
| `transactions` | Implemented | create/import/transfer/list/get/update/split/delete | No change |
| `transaction_lines` | Implemented (nested) | managed inside transaction payloads | Keep nested |
| `tags` | Missing | none | Add CRUD under budgets (`plans/tags-api-plan.md`) |
| `transaction_line_tags` | Implemented (nested) | managed via transaction line `tag_ids` | Keep nested |

## Recommended Sequence
1. Implement categories, payees, and tags first.
2. Add `users` read endpoint (`/users/me`).
3. Add integration tests that verify transaction behavior after category/payee/tag deletion.

## Cross-Cutting Rules
- Auth and authorization: keep `require_budget_member` for all budget-scoped routes.
- Validation flow: route -> service -> data access (same pattern as existing modules).
- Conflict behavior: return `409` for duplicate names within a budget.
- Unknown references: return `404` for resource lookup endpoints and `400` for invalid foreign references in transaction payloads (current behavior).
- Updates: continue using `extract_updates` so empty payloads return `400` and null fields are rejected with `422`.
- Ordering:
  - `categories`: `sort_order ASC`, `name ASC`, `id ASC`.
  - `payees`: `name ASC`, `id ASC`.
  - `tags`: `name ASC`, `id ASC`.

## Done Criteria
- All missing table-backed resources have routers, services, data_access modules, models, and tests.
- `budget_api/main.py` mounts all new routers.
- Test suite includes happy path, validation, conflict, permission, and cross-budget scoping checks for each new resource.
