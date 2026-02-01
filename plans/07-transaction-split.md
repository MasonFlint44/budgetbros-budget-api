# Feature Plan: Transaction Split (Rewrite Lines)

## Scope
Rewrite all lines for a non-transfer transaction.

## Endpoint
- POST /budgets/{budget_id}/transactions/{transaction_id}/split

## Models
- TransactionSplitCreate (lines: list[TransactionLineCreate])

## Service rules
- Verify budget membership.
- Load transaction + existing lines.
- Forbid splitting transfer transactions (400).
- Validate all new lines use the same account_id as the existing transaction.
- Treat split as non-transfer; category_id optional on lines.
- Replace all existing lines with new lines (atomic); total may change.

## Data access
- replace_transaction_lines (used by split endpoint)
- get_transaction (with lines)

## Tests
- split line (line replacement; total can change)
- split transfer -> 400
