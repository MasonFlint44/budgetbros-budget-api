from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import CategoriesDataAccess
from budget_api.models import Budget, Category


class CategoriesService:
    def __init__(
        self,
        categories_store: CategoriesDataAccess = Depends(),
    ) -> None:
        self._categories_store = categories_store

    async def _require_budget_category(
        self, budget: Budget, category_id: uuid.UUID
    ) -> Category:
        category = await self._categories_store.get_category(category_id)
        if category is None or category.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return category

    async def _validate_parent_id(
        self,
        *,
        budget: Budget,
        parent_id: uuid.UUID | None,
        category_id: uuid.UUID | None = None,
    ) -> None:
        if parent_id is None:
            return

        if category_id is not None and parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent.",
            )

        parent = await self._categories_store.get_category(parent_id)
        if parent is None or parent.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found.",
            )

        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nested categories cannot be deeper than one level.",
            )

    async def create_category(
        self,
        *,
        budget: Budget,
        name: str,
        parent_id: uuid.UUID | None,
        is_archived: bool,
        sort_order: int,
    ) -> Category:
        existing_category = await self._categories_store.get_category_by_name(
            budget.id, name
        )
        if existing_category is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category name already exists.",
            )

        await self._validate_parent_id(
            budget=budget,
            parent_id=parent_id,
        )

        return await self._categories_store.create_category(
            budget_id=budget.id,
            name=name,
            parent_id=parent_id,
            is_archived=is_archived,
            sort_order=sort_order,
        )

    async def list_categories(self, budget: Budget) -> list[Category]:
        return await self._categories_store.list_categories_by_budget(budget.id)

    async def get_category(self, budget: Budget, category_id: uuid.UUID) -> Category:
        return await self._require_budget_category(budget, category_id)

    async def update_category(
        self,
        budget: Budget,
        category_id: uuid.UUID,
        updates: dict[str, object],
    ) -> Category:
        category = await self._require_budget_category(budget, category_id)

        if "name" in updates:
            existing_category = await self._categories_store.get_category_by_name(
                budget.id,
                str(updates["name"]),
                exclude_category_id=category.id,
            )
            if existing_category is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category name already exists.",
                )

        if "parent_id" in updates:
            parent_id = updates["parent_id"]
            if parent_id is not None and not isinstance(parent_id, uuid.UUID):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent category not found.",
                )

            if parent_id is not None:
                has_children = await self._categories_store.has_children(category.id)
                if has_children:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nested categories cannot be deeper than one level.",
                    )

            await self._validate_parent_id(
                budget=budget,
                parent_id=parent_id,
                category_id=category.id,
            )

        updated_category = await self._categories_store.update_category(
            category.id, updates
        )
        if updated_category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return updated_category

    async def delete_category(self, budget: Budget, category_id: uuid.UUID) -> None:
        await self._require_budget_category(budget, category_id)
        deleted = await self._categories_store.delete_category(category_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
