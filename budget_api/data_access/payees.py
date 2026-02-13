from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Payee
from budget_api.tables import PayeesTable


class PayeesDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_payee(self, payee_id: uuid.UUID) -> Payee | None:
        payee = await self._session.get(PayeesTable, payee_id)
        if payee is None:
            return None
        return _to_payee(payee)

    async def get_payee_by_name(
        self,
        budget_id: uuid.UUID,
        name: str,
        *,
        exclude_payee_id: uuid.UUID | None = None,
    ) -> Payee | None:
        statement = select(PayeesTable).where(
            PayeesTable.budget_id == budget_id,
            PayeesTable.name == name,
        )
        if exclude_payee_id is not None:
            statement = statement.where(PayeesTable.id != exclude_payee_id)
        result = await self._session.execute(statement)
        payee = result.scalar_one_or_none()
        if payee is None:
            return None
        return _to_payee(payee)

    async def list_payees_by_budget(self, budget_id: uuid.UUID) -> list[Payee]:
        result = await self._session.execute(
            select(PayeesTable)
            .where(PayeesTable.budget_id == budget_id)
            .order_by(PayeesTable.name, PayeesTable.id)
        )
        return [_to_payee(payee) for payee in result.scalars()]

    async def create_payee(self, *, budget_id: uuid.UUID, name: str) -> Payee:
        payee = PayeesTable(
            budget_id=budget_id,
            name=name,
        )
        self._session.add(payee)
        await self._session.flush()
        await self._session.refresh(payee)
        return _to_payee(payee)

    async def update_payee(
        self, payee_id: uuid.UUID, updates: dict[str, object]
    ) -> Payee | None:
        payee = await self._session.get(PayeesTable, payee_id)
        if payee is None:
            return None
        for field, value in updates.items():
            setattr(payee, field, value)
        await self._session.flush()
        await self._session.refresh(payee)
        return _to_payee(payee)

    async def delete_payee(self, payee_id: uuid.UUID) -> bool:
        payee = await self._session.get(PayeesTable, payee_id)
        if payee is None:
            return False
        await self._session.delete(payee)
        await self._session.flush()
        return True


def _to_payee(payee: PayeesTable) -> Payee:
    return Payee(
        id=payee.id,
        budget_id=payee.budget_id,
        name=payee.name,
    )
