from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, status

from budget_api.data_access import (
    AccountsDataAccess,
    BudgetsDataAccess,
    TransactionsDataAccess,
)
from budget_api.models import (
    Transaction,
    TransactionCreate,
    TransactionLineDraft,
    TransactionStatus,
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


class TransactionsService:
    def __init__(
        self,
        transactions_store: TransactionsDataAccess = Depends(),
        budgets_store: BudgetsDataAccess = Depends(),
        accounts_store: AccountsDataAccess = Depends(),
    ) -> None:
        self._transactions_store = transactions_store
        self._budgets_store = budgets_store
        self._accounts_store = accounts_store

    async def _get_budget_for_member(
        self, budget_id: uuid.UUID, user_id: uuid.UUID, *, detail: str
    ):
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        is_member = await self._budgets_store.budget_member_exists(budget_id, user_id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        return budget

    async def create_transaction(
        self,
        *,
        budget_id: uuid.UUID,
        payload: TransactionCreate,
        user_id: uuid.UUID,
    ) -> Transaction:
        await self._get_budget_for_member(
            budget_id, user_id, detail="Not authorized to create transactions."
        )

        line = payload.line
        if line.amount_minor == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be non-zero.",
            )

        account = await self._accounts_store.get_account(line.account_id)
        if account is None or account.budget_id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found.",
            )

        if line.category_id is not None:
            category_ok = await self._transactions_store.category_exists_in_budget(
                line.category_id, budget_id
            )
            if not category_ok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category not found.",
                )

        if line.payee_id is not None:
            payee_ok = await self._transactions_store.payee_exists_in_budget(
                line.payee_id, budget_id
            )
            if not payee_ok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payee not found.",
                )

        tag_ids = _dedupe_tag_ids(line.tag_ids or [])
        if tag_ids:
            existing_tag_ids = await self._transactions_store.list_tag_ids_in_budget(
                tag_ids, budget_id
            )
            if existing_tag_ids != set(tag_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tag not found.",
                )

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
