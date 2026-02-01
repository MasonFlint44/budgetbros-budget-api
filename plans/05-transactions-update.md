# Feature Plan: Transactions Update

## Scope
Update transaction fields and edit existing lines (no add/remove).

## Endpoint
- PATCH /budgets/{budget_id}/transactions/{transaction_id}

## Models
- TransactionLineUpdate (line_id + editable fields)
- TransactionUpdate (transaction fields + optional line updates)
- TransactionResponse (lines optional when include_lines=false)

## Service rules
- Verify budget membership.
- Ensure transaction belongs to budget_id in path.
- Validate updated account/category/payee references.
- Line update rules:
  - unknown line_id, duplicate line_id, or line not in transaction -> 400.
  - missing lines unchanged.
- Revalidate invariants after edits:
  - Non-transfer: category_id optional, must use a single account_id.
  - Transfer: two lines with distinct account_ids, category_id null on both, net-zero sum.
  - If neither valid transfer nor valid non-transfer -> 400.
- Handle import_id uniqueness on update -> 409.

## Data access
- update_transaction
- get_transaction (with lines)
- get_transaction_line (for validation)

## Tests
- update transaction fields
- update with line edits (no add/remove)
- update with unknown/duplicate line_id -> 400
- update with line_id from another transaction -> 400
- update rejects non-transfer with multiple account_ids
- update invalid transfer invariants -> 400
