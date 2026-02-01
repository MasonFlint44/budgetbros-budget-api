# Feature Plan: Transactions Create

## Scope
Create a non-transfer transaction with exactly one line.

## Endpoint
- POST /budgets/{budget_id}/transactions

## Models
- TransactionLineCreate (optional tag_ids)
- TransactionCreate (includes line: TransactionLineCreate)
- TransactionLineResponse
- TransactionResponse (lines optional when include_lines=false)

## Service rules
- Verify budget membership.
- Validate budget exists.
- Validate account_id, category_id (if provided), payee_id (if provided) belong to budget.
- Enforce amount_minor != 0.
- Normalize status/posted_at.
- Create transaction + one line in a single session.

## Data access
- create_transaction
- create_transaction_lines

## Router integration
- Add budget_api/routers/transactions.py (create endpoint).
- Export in budget_api/routers/__init__.py and register in budget_api/main.py.

## Tests
- create transaction (line persisted, fields echoed)
- create with unknown account/category/payee -> 400/404
- create with amount_minor == 0 -> 400
