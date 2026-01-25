from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Budget
from budget_api.tables import BudgetsTable


class BudgetsDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_budget(self, budget_id: uuid.UUID) -> Budget | None:
        budget = await self._session.get(BudgetsTable, budget_id)
        if budget is None:
            return None
        return _to_budget(budget)

    async def list_budgets(self) -> list[Budget]:
        result = await self._session.execute(
            select(BudgetsTable).order_by(BudgetsTable.created_at)
        )
        return [_to_budget(budget) for budget in result.scalars()]

    async def create_budget(
        self, *, name: str, base_currency_code: str
    ) -> Budget:
        budget = BudgetsTable(name=name, base_currency_code=base_currency_code)
        self._session.add(budget)
        await self._session.flush()
        await self._session.refresh(budget)
        return _to_budget(budget)

    async def update_budget(
        self, budget_id: uuid.UUID, updates: dict[str, object]
    ) -> Budget | None:
        budget = await self._session.get(BudgetsTable, budget_id)
        if budget is None:
            return None
        for field, value in updates.items():
            setattr(budget, field, value)
        await self._session.flush()
        await self._session.refresh(budget)
        return _to_budget(budget)

    async def delete(self, budget_id: uuid.UUID) -> bool:
        budget = await self._session.get(BudgetsTable, budget_id)
        if budget is None:
            return False
        await self._session.delete(budget)
        await self._session.flush()
        return True


def _to_budget(budget: BudgetsTable) -> Budget:
    return Budget(
        id=budget.id,
        name=budget.name,
        base_currency_code=budget.base_currency_code,
        created_at=budget.created_at,
    )
