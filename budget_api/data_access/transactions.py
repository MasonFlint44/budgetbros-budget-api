from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from fastapi import Depends
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from budget_api import db
from budget_api.models import (
    Transaction,
    TransactionLine,
    TransactionLineDraft,
    TransactionLineUpdate,
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
        statement = (
            select(TransactionsTable)
            .where(TransactionsTable.budget_id == budget_id)
            .order_by(
                desc(TransactionsTable.posted_at),
                desc(TransactionsTable.created_at),
                desc(TransactionsTable.id),
            )
        )
        if include_lines:
            statement = statement.options(
                selectinload(TransactionsTable.lines).selectinload(
                    TransactionLinesTable.tag_links
                )
            )

        result = await self._session.execute(statement)
        transactions = list(result.scalars().unique())
        if not include_lines or not transactions:
            return [_to_transaction(transaction) for transaction in transactions]

        return [
            _to_transaction(
                transaction, lines=_to_transaction_lines(transaction.lines)
            )
            for transaction in transactions
        ]

    async def get_transaction(
        self, transaction_id: uuid.UUID, *, include_lines: bool = True
    ) -> Transaction | None:
        options = []
        if include_lines:
            options = [
                selectinload(TransactionsTable.lines).selectinload(
                    TransactionLinesTable.tag_links
                )
            ]
        transaction = await self._session.get(
            TransactionsTable, transaction_id, options=options
        )
        if transaction is None:
            return None
        if not include_lines:
            return _to_transaction(transaction)

        return _to_transaction(transaction, lines=_to_transaction_lines(transaction.lines))

    async def update_transaction(
        self, transaction_id: uuid.UUID, updates: dict[str, object]
    ) -> Transaction | None:
        transaction = await self._session.get(TransactionsTable, transaction_id)
        if transaction is None:
            return None
        for field, value in updates.items():
            setattr(transaction, field, value)
        await self._session.flush()
        await self._session.refresh(transaction)
        return _to_transaction(transaction)

    async def delete_transaction(self, transaction_id: uuid.UUID) -> bool:
        transaction = await self._session.get(TransactionsTable, transaction_id)
        if transaction is None:
            return False
        await self._session.delete(transaction)
        await self._session.flush()
        return True

    async def update_transaction_lines(
        self, line_updates: Sequence[TransactionLineUpdate]
    ) -> None:
        if not line_updates:
            return
        for update in line_updates:
            line = await self._session.get(TransactionLinesTable, update.line_id)
            if line is None:
                continue
            updates = update.model_dump(exclude_unset=True)
            updates.pop("line_id", None)
            updates.pop("tag_ids", None)
            if not updates:
                continue
            for field, value in updates.items():
                setattr(line, field, value)
        await self._session.flush()

    async def replace_transaction_lines(
        self, transaction_id: uuid.UUID, lines: Sequence[TransactionLineDraft]
    ) -> list[TransactionLine]:
        await self._session.execute(
            delete(TransactionLinesTable).where(
                TransactionLinesTable.transaction_id == transaction_id
            )
        )
        await self._session.flush()
        if not lines:
            return []
        return await self.create_transaction_lines(transaction_id, lines)

    async def replace_transaction_line_tags(
        self, tag_updates: dict[uuid.UUID, Sequence[uuid.UUID]]
    ) -> None:
        if not tag_updates:
            return
        line_ids = list(tag_updates.keys())
        await self._session.execute(
            delete(TransactionLineTagsTable).where(
                TransactionLineTagsTable.line_id.in_(line_ids)
            )
        )
        tag_links: list[TransactionLineTagsTable] = []
        for line_id, tag_ids in tag_updates.items():
            for tag_id in tag_ids:
                tag_links.append(
                    TransactionLineTagsTable(line_id=line_id, tag_id=tag_id)
                )
        if tag_links:
            self._session.add_all(tag_links)
        await self._session.flush()


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


def _to_transaction_lines(
    lines: Sequence[TransactionLinesTable],
) -> list[TransactionLine]:
    sorted_lines = sorted(lines, key=lambda line: line.id)
    return [
        _to_transaction_line(line, tag_ids=_sorted_tag_ids(line))
        for line in sorted_lines
    ]


def _sorted_tag_ids(line: TransactionLinesTable) -> list[uuid.UUID]:
    if not line.tag_links:
        return []
    sorted_links = sorted(line.tag_links, key=lambda link: link.tag_id)
    return [link.tag_id for link in sorted_links]
