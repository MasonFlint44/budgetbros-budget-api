# Feature Plan: Schema + Diagrams

## Scope
Add ordering index for transactions and keep diagrams in sync.

## Changes
- Add composite index on transactions for list ordering:
  - (budget_id, posted_at desc, created_at desc, id desc)
- Update diagrams/tables.mmd to reflect the new index.

## Tests
- No direct tests; covered by list ordering behavior in transactions tests.
