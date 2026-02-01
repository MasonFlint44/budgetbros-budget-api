# Feature Plan: Transactions List

## Scope
List transactions for a budget with optional lines.

## Endpoint
- GET /budgets/{budget_id}/transactions

## Models
- TransactionResponse (lines optional when include_lines=false)

## Service rules
- Verify budget membership.
- Order by posted_at desc, then created_at desc, then id desc.
- include_lines defaults to true; allow ?include_lines=false.

## Data access
- list_transactions (ordered)
- get_transaction (with lines) or selectinload as needed

## Tests
- list ordering (posted_at desc + created_at/id tie-breakers)
- list respects budget scoping
- list include_lines=false omits lines
