# Feature Plan: Transactions Get By ID

## Scope
Fetch a single transaction by id with optional lines.

## Endpoint
- GET /budgets/{budget_id}/transactions/{transaction_id}

## Models
- TransactionResponse (lines optional when include_lines=false)

## Service rules
- Verify budget membership.
- Ensure transaction belongs to budget_id in path.
- include_lines defaults to true; allow ?include_lines=false.

## Data access
- get_transaction (with lines)

## Tests
- get transaction returns 200
- get include_lines=false omits lines
- get transaction from another budget -> 404
