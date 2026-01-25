import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.auth import get_or_create_current_user
from budget_api.models import (
    Budget,
    BudgetCreate,
    BudgetMember,
    BudgetMemberCreate,
    BudgetMemberResponse,
    BudgetResponse,
    BudgetUpdate,
    User,
)
from budget_api.services import BudgetsService

router = APIRouter(prefix="/budgets")


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    current_user: User = Depends(get_or_create_current_user),
    budgets_service: BudgetsService = Depends(),
) -> Budget:
    return await budgets_service.create_budget(
        name=payload.name,
        base_currency_code=payload.base_currency_code,
        owner_user_id=current_user.id,
    )


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    budgets_service: BudgetsService = Depends(),
    current_user: User = Depends(get_or_create_current_user),
) -> list[Budget]:
    return await budgets_service.list_budgets(current_user.id)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    budgets_service: BudgetsService = Depends(),
    current_user: User = Depends(get_or_create_current_user),
) -> Budget:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    return await budgets_service.update_budget(budget_id, updates, current_user.id)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    budgets_service: BudgetsService = Depends(),
    current_user: User = Depends(get_or_create_current_user),
) -> None:
    await budgets_service.delete_budget(budget_id, current_user.id)


@router.post("/{budget_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_budget_member(
    budget_id: uuid.UUID,
    payload: BudgetMemberCreate,
    budgets_service: BudgetsService = Depends(),
    _current_user: User = Depends(get_or_create_current_user),
) -> None:
    await budgets_service.add_budget_member(
        budget_id, payload.user_id, _current_user.id
    )


@router.delete(
    "/{budget_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_budget_member(
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    budgets_service: BudgetsService = Depends(),
    _current_user: User = Depends(get_or_create_current_user),
) -> None:
    await budgets_service.remove_budget_member(
        budget_id, user_id, _current_user.id
    )


@router.get("/{budget_id}/members", response_model=list[BudgetMemberResponse])
async def list_budget_members(
    budget_id: uuid.UUID,
    budgets_service: BudgetsService = Depends(),
    current_user: User = Depends(get_or_create_current_user),
) -> list[BudgetMember]:
    return await budgets_service.list_budget_members(
        budget_id, current_user.id
    )
