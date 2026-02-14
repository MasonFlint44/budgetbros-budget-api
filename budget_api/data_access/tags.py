from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Tag
from budget_api.tables import TagsTable


class TagsDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_tag(self, tag_id: uuid.UUID) -> Tag | None:
        tag = await self._session.get(TagsTable, tag_id)
        if tag is None:
            return None
        return _to_tag(tag)

    async def get_tag_by_name(
        self,
        budget_id: uuid.UUID,
        name: str,
        *,
        exclude_tag_id: uuid.UUID | None = None,
    ) -> Tag | None:
        statement = select(TagsTable).where(
            TagsTable.budget_id == budget_id,
            TagsTable.name == name,
        )
        if exclude_tag_id is not None:
            statement = statement.where(TagsTable.id != exclude_tag_id)
        result = await self._session.execute(statement)
        tag = result.scalar_one_or_none()
        if tag is None:
            return None
        return _to_tag(tag)

    async def list_tags_by_budget(self, budget_id: uuid.UUID) -> list[Tag]:
        result = await self._session.execute(
            select(TagsTable)
            .where(TagsTable.budget_id == budget_id)
            .order_by(TagsTable.name, TagsTable.id)
        )
        return [_to_tag(tag) for tag in result.scalars()]

    async def create_tag(self, *, budget_id: uuid.UUID, name: str) -> Tag:
        tag = TagsTable(
            budget_id=budget_id,
            name=name,
        )
        self._session.add(tag)
        await self._session.flush()
        await self._session.refresh(tag)
        return _to_tag(tag)

    async def update_tag(
        self, tag_id: uuid.UUID, updates: dict[str, object]
    ) -> Tag | None:
        tag = await self._session.get(TagsTable, tag_id)
        if tag is None:
            return None
        for field, value in updates.items():
            setattr(tag, field, value)
        await self._session.flush()
        await self._session.refresh(tag)
        return _to_tag(tag)

    async def delete_tag(self, tag_id: uuid.UUID) -> bool:
        tag = await self._session.get(TagsTable, tag_id)
        if tag is None:
            return False
        await self._session.delete(tag)
        await self._session.flush()
        return True


def _to_tag(tag: TagsTable) -> Tag:
    return Tag(
        id=tag.id,
        budget_id=tag.budget_id,
        name=tag.name,
    )
