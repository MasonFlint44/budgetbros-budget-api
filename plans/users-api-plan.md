# Users API Plan

## Scope
Expose minimal read API for authenticated user data from `users` table.

## Endpoints
- `GET /users/me`

## Contract
- Response model can reuse `User` dataclass through a new `UserResponse` pydantic model, or return a typed dict if preferred.
- Response fields:
  - `id`, `email`, `created_at`, `last_seen_at`

## Business Rules
- Endpoint is authenticated only.
- Data comes from `get_or_create_current_user`; no new write path required.
- Keep user discovery/search out of scope for v1 to avoid privacy leaks.

## File-Level Implementation
- Add `budget_api/routers/users.py`.
- Add `UserResponse` to `budget_api/models/users.py` (or a dedicated router-local schema).
- Update `budget_api/models/__init__.py` exports.
- Mount users router in `budget_api/main.py`.
- Optionally update `budget_api/routers/__init__.py`.

## Test Plan
Add `tests/test_users.py` with:
- `GET /users/me` returns authenticated user identity,
- `last_seen_at` is present and timezone-aware,
- unauthenticated request returns `401` (if route-level auth is later relaxed globally).

## Acceptance Criteria
- Clients can fetch canonical current-user record without parsing token claims.
- Endpoint does not expand user visibility beyond current user.
