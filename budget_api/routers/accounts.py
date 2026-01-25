import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import AccountCreate, AccountResponse, AccountUpdate
from budget_api.tables import AccountsTable, BudgetsTable, CurrenciesTable

router = APIRouter()


@router.post(
    "/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_account(
    payload: AccountCreate, session: AsyncSession = Depends(db.get_session)
) -> AccountsTable:
    budget = await session.get(BudgetsTable, payload.budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    currency_code = payload.currency_code.upper()
    result = await session.execute(
        select(CurrenciesTable).where(CurrenciesTable.code == currency_code)
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown currency code.",
        )

    existing_account = await session.execute(
        select(AccountsTable).where(
            AccountsTable.budget_id == payload.budget_id,
            AccountsTable.name == payload.name,
        )
    )
    if existing_account.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists.",
        )

    account = AccountsTable(
        budget_id=payload.budget_id,
        name=payload.name,
        type=payload.type,
        currency_code=currency_code,
        is_closed=payload.is_closed,
    )
    session.add(account)
    await session.flush()
    await session.refresh(account)
    return account


@router.get("/budgets/{budget_id}/accounts", response_model=list[AccountResponse])
async def list_accounts(
    budget_id: uuid.UUID, session: AsyncSession = Depends(db.get_session)
) -> list[AccountsTable]:
    budget = await session.get(BudgetsTable, budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    result = await session.execute(
        select(AccountsTable)
        .where(AccountsTable.budget_id == budget_id)
        .order_by(AccountsTable.created_at)
    )
    return list(result.scalars())


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    session: AsyncSession = Depends(db.get_session),
) -> AccountsTable:
    account = await session.get(AccountsTable, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    if "currency_code" in updates:
        currency_code = updates["currency_code"].upper()
        result = await session.execute(
            select(CurrenciesTable).where(CurrenciesTable.code == currency_code)
        )
        currency = result.scalar_one_or_none()
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown currency code.",
            )
        account.currency_code = currency_code

    if "name" in updates:
        existing_account = await session.execute(
            select(AccountsTable).where(
                AccountsTable.budget_id == account.budget_id,
                AccountsTable.name == updates["name"],
                AccountsTable.id != account.id,
            )
        )
        if existing_account.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account name already exists.",
            )
        account.name = updates["name"]

    if "type" in updates:
        account.type = updates["type"]

    if "is_closed" in updates:
        account.is_closed = updates["is_closed"]

    await session.flush()
    await session.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID, session: AsyncSession = Depends(db.get_session)
) -> None:
    account = await session.get(AccountsTable, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )
    await session.delete(account)
    await session.flush()
