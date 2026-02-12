from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Category
from budget_api.tables import CategoriesTable


class CategoriesDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_category(self, category_id: uuid.UUID) -> Category | None:
        category = await self._session.get(CategoriesTable, category_id)
        if category is None:
            return None
        return _to_category(category)

    async def get_category_by_name(
        self,
        budget_id: uuid.UUID,
        name: str,
        *,
        exclude_category_id: uuid.UUID | None = None,
    ) -> Category | None:
        statement = select(CategoriesTable).where(
            CategoriesTable.budget_id == budget_id,
            CategoriesTable.name == name,
        )
        if exclude_category_id is not None:
            statement = statement.where(CategoriesTable.id != exclude_category_id)
        result = await self._session.execute(statement)
        category = result.scalar_one_or_none()
        if category is None:
            return None
        return _to_category(category)

    async def list_categories_by_budget(self, budget_id: uuid.UUID) -> list[Category]:
        result = await self._session.execute(
            select(CategoriesTable)
            .where(CategoriesTable.budget_id == budget_id)
            .order_by(
                CategoriesTable.sort_order,
                CategoriesTable.name,
                CategoriesTable.id,
            )
        )
        return [_to_category(category) for category in result.scalars()]

    async def create_category(
        self,
        *,
        budget_id: uuid.UUID,
        name: str,
        parent_id: uuid.UUID | None,
        is_archived: bool,
        sort_order: int,
    ) -> Category:
        category = CategoriesTable(
            budget_id=budget_id,
            name=name,
            parent_id=parent_id,
            is_archived=is_archived,
            sort_order=sort_order,
        )
        self._session.add(category)
        await self._session.flush()
        await self._session.refresh(category)
        return _to_category(category)

    async def has_children(self, category_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(CategoriesTable.id).where(CategoriesTable.parent_id == category_id)
        )
        return result.scalar_one_or_none() is not None

    async def update_category(
        self, category_id: uuid.UUID, updates: dict[str, object]
    ) -> Category | None:
        category = await self._session.get(CategoriesTable, category_id)
        if category is None:
            return None
        for field, value in updates.items():
            setattr(category, field, value)
        await self._session.flush()
        await self._session.refresh(category)
        return _to_category(category)

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        category = await self._session.get(CategoriesTable, category_id)
        if category is None:
            return False
        await self._session.delete(category)
        await self._session.flush()
        return True


def _to_category(category: CategoriesTable) -> Category:
    return Category(
        id=category.id,
        budget_id=category.budget_id,
        name=category.name,
        parent_id=category.parent_id,
        is_archived=category.is_archived,
        sort_order=category.sort_order,
    )
