import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.models import Budget, BudgetCreate, BudgetResponse, BudgetUpdate
from budget_api.services import BudgetsService

router = APIRouter(prefix="/budgets")


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    budgets_service: BudgetsService = Depends(),
) -> Budget:
    return await budgets_service.create_budget(
        name=payload.name,
        base_currency_code=payload.base_currency_code,
    )


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    budgets_service: BudgetsService = Depends(),
) -> list[Budget]:
    return await budgets_service.list_budgets()


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    budgets_service: BudgetsService = Depends(),
) -> Budget:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    return await budgets_service.update_budget(budget_id, updates)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    budgets_service: BudgetsService = Depends(),
) -> None:
    await budgets_service.delete_budget(budget_id)
