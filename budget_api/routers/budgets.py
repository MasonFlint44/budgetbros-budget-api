import uuid

from fastapi import APIRouter, Depends, status

from budget_api.auth import get_or_create_current_user
from budget_api.dependencies import require_budget_member, require_budget_owner
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
from budget_api.routers.utils import extract_updates
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
    payload: BudgetUpdate,
    budget: Budget = Depends(require_budget_member("Not authorized to update budget.")),
    budgets_service: BudgetsService = Depends(),
) -> Budget:
    updates = extract_updates(payload)
    return await budgets_service.update_budget(budget, updates)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget: Budget = Depends(require_budget_owner("Not authorized to delete budget.")),
    budgets_service: BudgetsService = Depends(),
) -> None:
    await budgets_service.delete_budget(budget)


@router.post("/{budget_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_budget_member(
    payload: BudgetMemberCreate,
    budget: Budget = Depends(
        require_budget_owner("Not authorized to manage budget members.")
    ),
    budgets_service: BudgetsService = Depends(),
) -> None:
    await budgets_service.add_budget_member(budget, payload.user_id)


@router.delete("/{budget_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_budget_member(
    user_id: uuid.UUID,
    budget: Budget = Depends(
        require_budget_owner("Not authorized to manage budget members.")
    ),
    budgets_service: BudgetsService = Depends(),
) -> None:
    await budgets_service.remove_budget_member(budget, user_id)


@router.get("/{budget_id}/members", response_model=list[BudgetMemberResponse])
async def list_budget_members(
    budget: Budget = Depends(
        require_budget_member("Not authorized to view budget members.")
    ),
    budgets_service: BudgetsService = Depends(),
) -> list[BudgetMember]:
    return await budgets_service.list_budget_members(budget)
