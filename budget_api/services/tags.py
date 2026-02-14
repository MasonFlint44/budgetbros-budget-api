from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import TagsDataAccess
from budget_api.models import Budget, Tag


class TagsService:
    def __init__(
        self,
        tags_store: TagsDataAccess = Depends(),
    ) -> None:
        self._tags_store = tags_store

    async def _require_budget_tag(self, budget: Budget, tag_id: uuid.UUID) -> Tag:
        tag = await self._tags_store.get_tag(tag_id)
        if tag is None or tag.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found.",
            )
        return tag

    async def create_tag(
        self,
        *,
        budget: Budget,
        name: str,
    ) -> Tag:
        existing_tag = await self._tags_store.get_tag_by_name(budget.id, name)
        if existing_tag is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag name already exists.",
            )
        return await self._tags_store.create_tag(
            budget_id=budget.id,
            name=name,
        )

    async def list_tags(self, budget: Budget) -> list[Tag]:
        return await self._tags_store.list_tags_by_budget(budget.id)

    async def get_tag(self, budget: Budget, tag_id: uuid.UUID) -> Tag:
        return await self._require_budget_tag(budget, tag_id)

    async def update_tag(
        self,
        budget: Budget,
        tag_id: uuid.UUID,
        updates: dict[str, object],
    ) -> Tag:
        tag = await self._require_budget_tag(budget, tag_id)

        if "name" in updates:
            existing_tag = await self._tags_store.get_tag_by_name(
                budget.id,
                str(updates["name"]),
                exclude_tag_id=tag.id,
            )
            if existing_tag is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Tag name already exists.",
                )

        updated_tag = await self._tags_store.update_tag(tag.id, updates)
        if updated_tag is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found.",
            )
        return updated_tag

    async def delete_tag(self, budget: Budget, tag_id: uuid.UUID) -> None:
        await self._require_budget_tag(budget, tag_id)
        deleted = await self._tags_store.delete_tag(tag_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found.",
            )
