from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from fastapi import Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import (
    Transaction,
    TransactionLine,
    TransactionLineDraft,
    TransactionStatus,
)
from budget_api.tables import (
    CategoriesTable,
    PayeesTable,
    TagsTable,
    TransactionLinesTable,
    TransactionLineTagsTable,
    TransactionsTable,
)


class TransactionsDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def create_transaction(
        self,
        *,
        budget_id: uuid.UUID,
        posted_at: datetime,
        status: TransactionStatus,
        notes: str | None,
        import_id: str | None,
    ) -> Transaction:
        transaction = TransactionsTable(
            budget_id=budget_id,
            posted_at=posted_at,
            status=status.value,
            notes=notes,
            import_id=import_id,
        )
        self._session.add(transaction)
        await self._session.flush()
        await self._session.refresh(transaction)
        return _to_transaction(transaction)

    async def create_transaction_lines(
        self, transaction_id: uuid.UUID, lines: Sequence[TransactionLineDraft]
    ) -> list[TransactionLine]:
        line_rows: list[TransactionLinesTable] = []
        for line in lines:
            row = TransactionLinesTable(
                transaction_id=transaction_id,
                account_id=line.account_id,
                category_id=line.category_id,
                payee_id=line.payee_id,
                amount_minor=line.amount_minor,
                memo=line.memo,
            )
            self._session.add(row)
            line_rows.append(row)
        await self._session.flush()

        tag_links: list[TransactionLineTagsTable] = []
        for row, line in zip(line_rows, lines):
            for tag_id in line.tag_ids:
                tag_links.append(
                    TransactionLineTagsTable(line_id=row.id, tag_id=tag_id)
                )
        if tag_links:
            self._session.add_all(tag_links)
            await self._session.flush()

        return [
            _to_transaction_line(row, tag_ids=line.tag_ids)
            for row, line in zip(line_rows, lines)
        ]

    async def category_exists_in_budget(
        self, category_id: uuid.UUID, budget_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(CategoriesTable.id).where(
                CategoriesTable.id == category_id,
                CategoriesTable.budget_id == budget_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def payee_exists_in_budget(
        self, payee_id: uuid.UUID, budget_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(PayeesTable.id).where(
                PayeesTable.id == payee_id,
                PayeesTable.budget_id == budget_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_tag_ids_in_budget(
        self, tag_ids: Sequence[uuid.UUID], budget_id: uuid.UUID
    ) -> set[uuid.UUID]:
        if not tag_ids:
            return set()
        result = await self._session.execute(
            select(TagsTable.id).where(
                TagsTable.budget_id == budget_id,
                TagsTable.id.in_(tag_ids),
            )
        )
        return set(result.scalars().all())

    async def list_transactions(
        self, budget_id: uuid.UUID, *, include_lines: bool = True
    ) -> list[Transaction]:
        result = await self._session.execute(
            select(TransactionsTable)
            .where(TransactionsTable.budget_id == budget_id)
            .order_by(
                desc(TransactionsTable.posted_at),
                desc(TransactionsTable.created_at),
                desc(TransactionsTable.id),
            )
        )
        transactions = list(result.scalars())
        if not include_lines or not transactions:
            return [_to_transaction(transaction) for transaction in transactions]

        transaction_ids = [transaction.id for transaction in transactions]
        lines_result = await self._session.execute(
            select(TransactionLinesTable)
            .where(TransactionLinesTable.transaction_id.in_(transaction_ids))
            .order_by(TransactionLinesTable.transaction_id, TransactionLinesTable.id)
        )
        line_rows = list(lines_result.scalars())

        tag_ids_by_line: dict[uuid.UUID, list[uuid.UUID]] = {
            line.id: [] for line in line_rows
        }
        line_ids = [line.id for line in line_rows]
        if line_ids:
            tag_rows = await self._session.execute(
                select(
                    TransactionLineTagsTable.line_id, TransactionLineTagsTable.tag_id
                )
                .where(TransactionLineTagsTable.line_id.in_(line_ids))
                .order_by(TransactionLineTagsTable.line_id, TransactionLineTagsTable.tag_id)
            )
            for line_id, tag_id in tag_rows.all():
                tag_ids_by_line.setdefault(line_id, []).append(tag_id)

        lines_by_transaction: dict[uuid.UUID, list[TransactionLine]] = {
            transaction_id: [] for transaction_id in transaction_ids
        }
        for line in line_rows:
            lines_by_transaction.setdefault(line.transaction_id, []).append(
                _to_transaction_line(line, tag_ids=tag_ids_by_line.get(line.id, []))
            )

        return [
            _to_transaction(
                transaction, lines=lines_by_transaction.get(transaction.id, [])
            )
            for transaction in transactions
        ]

    async def get_transaction(
        self, transaction_id: uuid.UUID, *, include_lines: bool = True
    ) -> Transaction | None:
        transaction = await self._session.get(TransactionsTable, transaction_id)
        if transaction is None:
            return None
        if not include_lines:
            return _to_transaction(transaction)

        lines_result = await self._session.execute(
            select(TransactionLinesTable)
            .where(TransactionLinesTable.transaction_id == transaction_id)
            .order_by(TransactionLinesTable.id)
        )
        line_rows = list(lines_result.scalars())

        tag_ids_by_line: dict[uuid.UUID, list[uuid.UUID]] = {
            line.id: [] for line in line_rows
        }
        line_ids = [line.id for line in line_rows]
        if line_ids:
            tag_rows = await self._session.execute(
                select(TransactionLineTagsTable.line_id, TransactionLineTagsTable.tag_id)
                .where(TransactionLineTagsTable.line_id.in_(line_ids))
                .order_by(TransactionLineTagsTable.line_id, TransactionLineTagsTable.tag_id)
            )
            for line_id, tag_id in tag_rows.all():
                tag_ids_by_line.setdefault(line_id, []).append(tag_id)

        lines = [
            _to_transaction_line(line, tag_ids=tag_ids_by_line.get(line.id, []))
            for line in line_rows
        ]
        return _to_transaction(transaction, lines=lines)


def _to_transaction(
    transaction: TransactionsTable, *, lines: Sequence[TransactionLine] | None = None
) -> Transaction:
    return Transaction(
        id=transaction.id,
        budget_id=transaction.budget_id,
        posted_at=transaction.posted_at,
        status=TransactionStatus(transaction.status),
        notes=transaction.notes,
        import_id=transaction.import_id,
        created_at=transaction.created_at,
        lines=list(lines) if lines is not None else None,
    )


def _to_transaction_line(
    line: TransactionLinesTable, *, tag_ids: Sequence[uuid.UUID] | None = None
) -> TransactionLine:
    return TransactionLine(
        id=line.id,
        transaction_id=line.transaction_id,
        account_id=line.account_id,
        category_id=line.category_id,
        payee_id=line.payee_id,
        amount_minor=line.amount_minor,
        memo=line.memo,
        tag_ids=list(tag_ids) if tag_ids else [],
    )
