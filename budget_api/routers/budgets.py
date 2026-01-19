import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import BudgetCreate, BudgetResponse, BudgetUpdate
from budget_api.tables import Budget, Currency

router = APIRouter(prefix="/budgets")


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate, session: AsyncSession = Depends(db.get_session)
) -> Budget:
    currency_code = payload.base_currency_code.upper()
    result = await session.execute(
        select(Currency).where(Currency.code == currency_code)
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown base currency code.",
        )
    budget = Budget(name=payload.name, base_currency_code=currency_code)
    session.add(budget)
    await session.flush()
    await session.refresh(budget)
    return budget


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    session: AsyncSession = Depends(db.get_session),
) -> list[Budget]:
    result = await session.execute(select(Budget).order_by(Budget.created_at))
    return list(result.scalars())


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    session: AsyncSession = Depends(db.get_session),
) -> Budget:
    budget = await session.get(Budget, budget_id)
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
        result = await session.execute(
            select(Currency).where(Currency.code == currency_code)
        )
        currency = result.scalar_one_or_none()
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown base currency code.",
            )
        budget.base_currency_code = currency_code

    if "name" in updates:
        budget.name = updates["name"]

    await session.flush()
    await session.refresh(budget)
    return budget
