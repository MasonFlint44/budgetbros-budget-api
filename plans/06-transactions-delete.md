# Feature Plan: Transactions Delete

## Scope
Delete a transaction and cascade its lines.

## Endpoint
- DELETE /budgets/{budget_id}/transactions/{transaction_id}

## Service rules
- Verify budget membership.
- Ensure transaction belongs to budget_id in path.
- Delete transaction (cascade removes lines).

## Data access
- delete_transaction

## Tests
- delete transaction removes it and its lines
- delete transaction from another budget -> 404
