# Transactions API Feature Plans (Ordered)

## Implementation order
1) 01-account-budget-currency.md
2) 02-transactions-create.md
3) 03-transactions-list.md
4) 04-transactions-get.md
5) 05-transactions-update.md
6) 06-transactions-delete.md
7) 07-transaction-split.md
8) 08-transfers.md
9) 09-bulk-import.md
10) 10-schema-diagrams.md

## Shared conventions
- Budget-scoped routes under `/budgets/{budget_id}/...`.
- `transaction_id` must belong to the budget in the path.
- `include_lines` defaults to true; support `?include_lines=false` on list and get-by-id.
- Ordering: `posted_at desc, created_at desc, id desc`.
- Auth: use `Depends(get_or_create_current_user)` and membership checks.
- Transfers are separate endpoints; non-transfer transactions use a single account_id and may omit category_id.
