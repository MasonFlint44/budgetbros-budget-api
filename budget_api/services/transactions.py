from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, status

from budget_api.data_access import AccountsDataAccess, TransactionsDataAccess
from budget_api.models import (
    Transaction,
    TransactionCreate,
    TransactionLineDraft,
    TransactionLineUpdate,
    TransactionStatus,
    TransactionUpdate,
)


_ALLOWED_STATUSES = {status.value for status in TransactionStatus}


def _normalize_posted_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_status(raw_status: str | None) -> TransactionStatus:
    if raw_status is None:
        return TransactionStatus.posted
    normalized = raw_status.strip().lower()
    if normalized not in _ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status.",
        )
    return TransactionStatus(normalized)


def _dedupe_tag_ids(tag_ids: Iterable[uuid.UUID]) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    deduped: list[uuid.UUID] = []
    for tag_id in tag_ids:
        if tag_id in seen:
            continue
        seen.add(tag_id)
        deduped.append(tag_id)
    return deduped


@dataclass(slots=True)
class LineSnapshot:
    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    payee_id: uuid.UUID | None
    amount_minor: int
    memo: str | None
    tag_ids: list[uuid.UUID]


def _is_valid_transfer(lines: list[LineSnapshot]) -> bool:
    if len(lines) != 2:
        return False
    account_ids = {line.account_id for line in lines}
    if len(account_ids) != 2:
        return False
    if any(line.category_id is not None for line in lines):
        return False
    total = sum(line.amount_minor for line in lines)
    return total == 0


def _is_valid_non_transfer(lines: list[LineSnapshot]) -> bool:
    if not lines:
        return False
    account_ids = {line.account_id for line in lines}
    return len(account_ids) == 1


class TransactionsService:
    def __init__(
        self,
        transactions_store: TransactionsDataAccess = Depends(),
        accounts_store: AccountsDataAccess = Depends(),
    ) -> None:
        self._transactions_store = transactions_store
        self._accounts_store = accounts_store

    async def _require_account(
        self,
        budget_id: uuid.UUID,
        account_id: uuid.UUID,
        *,
        cache: dict[uuid.UUID, bool] | None = None,
    ) -> None:
        if cache is not None and account_id in cache:
            if not cache[account_id]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account not found.",
                )
            return
        account = await self._accounts_store.get_account(account_id)
        ok = account is not None and account.budget_id == budget_id
        if cache is not None:
            cache[account_id] = ok
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found.",
            )

    async def _require_category(
        self,
        budget_id: uuid.UUID,
        category_id: uuid.UUID,
        *,
        cache: dict[uuid.UUID, bool] | None = None,
    ) -> None:
        if cache is not None and category_id in cache:
            if not cache[category_id]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category not found.",
                )
            return
        ok = await self._transactions_store.category_exists_in_budget(
            category_id, budget_id
        )
        if cache is not None:
            cache[category_id] = ok
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found.",
            )

    async def _require_payee(
        self,
        budget_id: uuid.UUID,
        payee_id: uuid.UUID,
        *,
        cache: dict[uuid.UUID, bool] | None = None,
    ) -> None:
        if cache is not None and payee_id in cache:
            if not cache[payee_id]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payee not found.",
                )
            return
        ok = await self._transactions_store.payee_exists_in_budget(
            payee_id, budget_id
        )
        if cache is not None:
            cache[payee_id] = ok
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payee not found.",
            )

    async def _require_tags(
        self, budget_id: uuid.UUID, tag_ids: Iterable[uuid.UUID]
    ) -> list[uuid.UUID]:
        deduped = _dedupe_tag_ids(tag_ids)
        if not deduped:
            return []
        existing_tag_ids = await self._transactions_store.list_tag_ids_in_budget(
            deduped, budget_id
        )
        if existing_tag_ids != set(deduped):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag not found.",
            )
        return deduped

    async def create_transaction(
        self,
        *,
        budget_id: uuid.UUID,
        payload: TransactionCreate,
    ) -> Transaction:
        line = payload.line
        if line.amount_minor == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be non-zero.",
            )

        await self._require_account(budget_id, line.account_id)

        if line.category_id is not None:
            await self._require_category(budget_id, line.category_id)

        if line.payee_id is not None:
            await self._require_payee(budget_id, line.payee_id)

        tag_ids = await self._require_tags(budget_id, line.tag_ids or [])

        normalized_status = _normalize_status(payload.status)
        posted_at = _normalize_posted_at(payload.posted_at)

        transaction = await self._transactions_store.create_transaction(
            budget_id=budget_id,
            posted_at=posted_at,
            status=normalized_status,
            notes=payload.notes,
            import_id=payload.import_id,
        )

        lines = await self._transactions_store.create_transaction_lines(
            transaction.id,
            [
                TransactionLineDraft(
                    account_id=line.account_id,
                    category_id=line.category_id,
                    payee_id=line.payee_id,
                    amount_minor=line.amount_minor,
                    memo=line.memo,
                    tag_ids=tag_ids,
                )
            ],
        )

        return Transaction(
            id=transaction.id,
            budget_id=transaction.budget_id,
            posted_at=transaction.posted_at,
            status=transaction.status,
            notes=transaction.notes,
            import_id=transaction.import_id,
            created_at=transaction.created_at,
            lines=lines,
        )

    async def list_transactions(
        self,
        budget_id: uuid.UUID,
        *,
        include_lines: bool = True,
    ) -> list[Transaction]:
        return await self._transactions_store.list_transactions(
            budget_id, include_lines=include_lines
        )

    async def get_transaction(
        self,
        budget_id: uuid.UUID,
        transaction_id: uuid.UUID,
        *,
        include_lines: bool = True,
    ) -> Transaction:
        transaction = await self._transactions_store.get_transaction(
            transaction_id, include_lines=include_lines
        )
        if transaction is None or transaction.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
        return transaction

    async def update_transaction(
        self,
        *,
        budget_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TransactionUpdate,
    ) -> Transaction:
        transaction = await self._transactions_store.get_transaction(
            transaction_id, include_lines=True
        )
        if transaction is None or transaction.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        raw_updates = payload.model_dump(exclude_unset=True)
        if not raw_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        transaction_updates: dict[str, object] = {}
        if "posted_at" in raw_updates:
            posted_at = raw_updates["posted_at"]
            if posted_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Posted at is required.",
                )
            transaction_updates["posted_at"] = _normalize_posted_at(posted_at)

        if "status" in raw_updates:
            raw_status = raw_updates["status"]
            if raw_status is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status is required.",
                )
            normalized_status = _normalize_status(raw_status)
            transaction_updates["status"] = normalized_status.value

        if "notes" in raw_updates:
            transaction_updates["notes"] = raw_updates["notes"]

        if "import_id" in raw_updates:
            import_id = raw_updates["import_id"]
            if import_id != transaction.import_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Import id cannot be updated.",
                )
            if len(raw_updates) == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Import id cannot be updated.",
                )

        line_updates_payload = None
        if "lines" in raw_updates:
            line_updates_payload = payload.lines
            if line_updates_payload is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Lines cannot be null.",
                )
            if not line_updates_payload:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No line updates provided.",
                )

        if not transaction_updates and not line_updates_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        existing_lines = transaction.lines or []
        line_snapshots: dict[uuid.UUID, LineSnapshot] = {
            line.id: LineSnapshot(
                id=line.id,
                account_id=line.account_id,
                category_id=line.category_id,
                payee_id=line.payee_id,
                amount_minor=line.amount_minor,
                memo=line.memo,
                tag_ids=list(line.tag_ids),
            )
            for line in existing_lines
        }

        line_updates_to_apply: list[TransactionLineUpdate] = []
        tag_updates: dict[uuid.UUID, list[uuid.UUID]] = {}

        account_cache: dict[uuid.UUID, bool] = {}
        category_cache: dict[uuid.UUID, bool] = {}
        payee_cache: dict[uuid.UUID, bool] = {}
        tag_ids_to_validate: list[uuid.UUID] = []

        if line_updates_payload:
            seen_line_ids: set[uuid.UUID] = set()
            for line_update in line_updates_payload:
                line_id = line_update.line_id
                if line_id in seen_line_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Duplicate line_id.",
                    )
                seen_line_ids.add(line_id)
                if line_id not in line_snapshots:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Line not found.",
                    )

                update_fields = line_update.model_dump(exclude_unset=True)
                update_fields.pop("line_id", None)
                if not update_fields:
                    continue

                snapshot = line_snapshots[line_id]
                line_update_db: dict[str, object] = {}

                if "account_id" in update_fields:
                    account_id = update_fields["account_id"]
                    if account_id is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Account not found.",
                        )
                    await self._require_account(
                        budget_id, account_id, cache=account_cache
                    )
                    snapshot.account_id = account_id
                    line_update_db["account_id"] = account_id

                if "category_id" in update_fields:
                    category_id = update_fields["category_id"]
                    if category_id is not None:
                        await self._require_category(
                            budget_id, category_id, cache=category_cache
                        )
                    snapshot.category_id = category_id
                    line_update_db["category_id"] = category_id

                if "payee_id" in update_fields:
                    payee_id = update_fields["payee_id"]
                    if payee_id is not None:
                        await self._require_payee(
                            budget_id, payee_id, cache=payee_cache
                        )
                    snapshot.payee_id = payee_id
                    line_update_db["payee_id"] = payee_id

                if "amount_minor" in update_fields:
                    amount_minor = update_fields["amount_minor"]
                    if amount_minor is None or amount_minor == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Amount must be non-zero.",
                        )
                    snapshot.amount_minor = amount_minor
                    line_update_db["amount_minor"] = amount_minor

                if "memo" in update_fields:
                    snapshot.memo = update_fields["memo"]
                    line_update_db["memo"] = update_fields["memo"]

                if "tag_ids" in update_fields:
                    raw_tag_ids = update_fields["tag_ids"]
                    if raw_tag_ids is None:
                        tag_ids: list[uuid.UUID] = []
                    else:
                        tag_ids = _dedupe_tag_ids(raw_tag_ids)
                    tag_updates[line_id] = tag_ids
                    tag_ids_to_validate.extend(tag_ids)
                    snapshot.tag_ids = tag_ids

                if line_update_db:
                    line_updates_to_apply.append(
                        TransactionLineUpdate(line_id=line_id, **line_update_db)
                    )

        if not transaction_updates and not line_updates_to_apply and not tag_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        if tag_ids_to_validate:
            await self._require_tags(budget_id, tag_ids_to_validate)

        updated_lines = list(line_snapshots.values())
        if not _is_valid_transfer(updated_lines) and not _is_valid_non_transfer(
            updated_lines
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction lines.",
            )

        if transaction_updates:
            updated = await self._transactions_store.update_transaction(
                transaction_id, transaction_updates
            )
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Transaction not found.",
                )

        if line_updates_to_apply:
            await self._transactions_store.update_transaction_lines(
                line_updates_to_apply
            )

        if tag_updates:
            await self._transactions_store.replace_transaction_line_tags(tag_updates)

        updated_transaction = await self._transactions_store.get_transaction(
            transaction_id, include_lines=True
        )
        if updated_transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
        return updated_transaction

    async def delete_transaction(
        self,
        *,
        budget_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> None:
        transaction = await self._transactions_store.get_transaction(
            transaction_id, include_lines=False
        )
        if transaction is None or transaction.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
        deleted = await self._transactions_store.delete_transaction(transaction_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )
