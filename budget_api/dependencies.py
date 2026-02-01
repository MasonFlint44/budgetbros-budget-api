from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.auth import get_or_create_current_user
from budget_api.data_access import BudgetsDataAccess
from budget_api.models import Budget, User


def require_budget_member(detail: str):
    async def _dependency(
        budget_id: uuid.UUID,
        current_user: User = Depends(get_or_create_current_user),
        budgets_store: BudgetsDataAccess = Depends(),
    ) -> Budget:
        budget = await budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        is_member = await budgets_store.budget_member_exists(budget_id, current_user.id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        return budget

    return _dependency


def require_budget_owner(detail: str):
    async def _dependency(
        budget_id: uuid.UUID,
        current_user: User = Depends(get_or_create_current_user),
        budgets_store: BudgetsDataAccess = Depends(),
    ) -> Budget:
        budget = await budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        is_owner = await budgets_store.budget_owner_exists(budget_id, current_user.id)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        return budget

    return _dependency
