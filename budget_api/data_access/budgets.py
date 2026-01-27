from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Budget, BudgetMember
from budget_api.tables import BudgetMembersTable, BudgetsTable, UsersTable


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
        self, *, name: str, base_currency_code: str, owner_user_id: uuid.UUID
    ) -> Budget:
        budget = BudgetsTable(
            name=name,
            base_currency_code=base_currency_code,
            owner_user_id=owner_user_id,
        )
        self._session.add(budget)
        await self._session.flush()
        await self._session.refresh(budget)
        return _to_budget(budget)

    async def list_budgets_for_user(self, user_id: uuid.UUID) -> list[Budget]:
        result = await self._session.execute(
            select(BudgetsTable)
            .join(BudgetMembersTable, BudgetMembersTable.budget_id == BudgetsTable.id)
            .where(BudgetMembersTable.user_id == user_id)
            .order_by(BudgetsTable.created_at)
        )
        return [_to_budget(budget) for budget in result.scalars()]

    async def user_exists(self, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(UsersTable.id).where(UsersTable.id == user_id)
        )
        return result.scalar_one_or_none() is not None

    async def budget_member_exists(
        self, budget_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(BudgetMembersTable.id).where(
                BudgetMembersTable.budget_id == budget_id,
                BudgetMembersTable.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def budget_owner_exists(
        self, budget_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(BudgetsTable.id).where(
                BudgetsTable.id == budget_id,
                BudgetsTable.owner_user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_budget_member(self, budget_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = BudgetMembersTable(budget_id=budget_id, user_id=user_id)
        self._session.add(member)
        await self._session.flush()

    async def remove_budget_member(
        self, budget_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
                BudgetMembersTable.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await self._session.delete(member)
        await self._session.flush()
        return True

    async def list_budget_members(self, budget_id: uuid.UUID) -> list[BudgetMember]:
        result = await self._session.execute(
            select(
                UsersTable.id,
                UsersTable.email,
                BudgetMembersTable.created_at,
            )
            .join(BudgetMembersTable, BudgetMembersTable.user_id == UsersTable.id)
            .where(BudgetMembersTable.budget_id == budget_id)
            .order_by(BudgetMembersTable.created_at)
        )
        return [
            BudgetMember(
                user_id=row.id,
                email=row.email,
                joined_at=row.created_at,
            )
            for row in result.all()
        ]

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
