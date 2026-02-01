# Feature Plan: Transfers

## Scope
Create transfers as two-line transactions.

## Endpoint
- POST /budgets/{budget_id}/transactions/transfer

## Models
- TransferCreate (from_account_id, to_account_id, amount_minor, posted_at, notes?, memo?, tag_ids?; no payee_id)

## Service rules
- Verify budget membership.
- Validate both accounts exist and belong to the budget.
- Enforce distinct account_ids.
- Enforce category_id null on both lines.
- Enforce net-zero: sum amounts == 0.
- Allow tag_ids; reject payee_id.
- Enforce budget currency consistency (all accounts share budget base currency).

## Data access
- create_transaction
- create_transaction_lines

## Tests
- transfer creates two lines with category_id null and net-zero sum
- reject same-account transfer
- reject non-zero sum
- reject payee_id on transfer
