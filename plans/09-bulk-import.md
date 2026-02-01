# Feature Plan: Bulk Import

## Scope
Import transactions in bulk with idempotency.

## Endpoint
- POST /budgets/{budget_id}/transactions/import

## Models
- TransactionBulkCreate (transactions: list[TransactionCreate])
- TransactionImportSummary (created_count, existing_count)

## Service rules
- Verify budget membership.
- All-or-nothing: validate all items before insert.
- If any item invalid -> 400 with index-based errors.
- If duplicate import_id in the same request -> 400.
- If import_id already exists in DB -> idempotent no-op.
- Response is summary-only: 201 if all new, otherwise 200.

## Data access
- list_existing_import_ids (for dedupe)
- create_transaction / create_transaction_lines for inserts

## Tests
- bulk import all-new -> 201
- bulk import with existing import_id -> 200 and counts
- bulk import duplicate import_id in request -> 400
