import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.data_access import BudgetsDataAccess, CurrenciesDataAccess
from budget_api.models import Budget, BudgetCreate, BudgetResponse, BudgetUpdate

router = APIRouter(prefix="/budgets")


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    budgets_store: BudgetsDataAccess = Depends(),
    currencies_store: CurrenciesDataAccess = Depends(),
) -> Budget:
    currency_code = payload.base_currency_code.upper()
    currency = await currencies_store.get_currency(currency_code)
    if currency is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown base currency code.",
        )
    return await budgets_store.create_budget(
        name=payload.name, base_currency_code=currency_code
    )


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    budgets_store: BudgetsDataAccess = Depends(),
) -> list[Budget]:
    return await budgets_store.list_budgets()


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    budgets_store: BudgetsDataAccess = Depends(),
    currencies_store: CurrenciesDataAccess = Depends(),
) -> Budget:
    budget = await budgets_store.get_budget(budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    if "base_currency_code" in updates:
        currency_code = updates["base_currency_code"].upper()
        currency = await currencies_store.get_currency(currency_code)
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown base currency code.",
            )
        updates["base_currency_code"] = currency_code

    updated_budget = await budgets_store.update_budget(budget_id, updates)
    if updated_budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )
    return updated_budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    budgets_store: BudgetsDataAccess = Depends(),
) -> None:
    deleted = await budgets_store.delete(budget_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )
