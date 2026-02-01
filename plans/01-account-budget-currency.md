# Feature Plan: Account Routes + Budget Currency Enforcement

## Scope
Align account routes to budget scope and enforce budget currency rules.

## Endpoints
- POST /budgets/{budget_id}/accounts (remove budget_id from body)
- PATCH /budgets/{budget_id}/accounts/{account_id}
- DELETE /budgets/{budget_id}/accounts/{account_id}
- GET /budgets/{budget_id}/accounts (require membership)
- Remove legacy /accounts and /accounts/{account_id} routes (breaking change)

## Models
- Update AccountCreate schema to remove budget_id.

## Service rules
- Require current_user for create/update/delete/list; verify membership.
- For update/delete, ensure account belongs to budget_id from path.
- Enforce account.currency_code == budget.base_currency_code on create/update.
- Budget base_currency_code updates deactivate all accounts (set is_active=false).

## Data access
- list_accounts_by_budget (for currency enforcement on create/update)
- count_active_accounts_by_budget (for budget currency changes)

## Router integration
- Update budget_api/routers/accounts.py routes and payload shape.
- Add current_user: User = Depends(get_or_create_current_user) to account endpoints.

## Tests
- account create/update rejects currency != budget base currency
- account list/create/update/delete require membership
- account update/delete reject mismatched budget_id in path
- budget base currency update blocked if any active accounts
- budget base currency update allowed if all accounts closed or none exist
