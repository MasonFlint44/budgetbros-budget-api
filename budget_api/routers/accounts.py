import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.data_access import (
    AccountsDataAccess,
    BudgetsDataAccess,
    CurrenciesDataAccess,
)
from budget_api.models import Account, AccountCreate, AccountResponse, AccountUpdate

router = APIRouter()


@router.post(
    "/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_account(
    payload: AccountCreate,
    accounts_store: AccountsDataAccess = Depends(),
    budgets_store: BudgetsDataAccess = Depends(),
    currencies_store: CurrenciesDataAccess = Depends(),
) -> Account:
    budget = await budgets_store.get_budget(payload.budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    currency_code = payload.currency_code.upper()
    currency = await currencies_store.get_currency(currency_code)
    if currency is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown currency code.",
        )

    existing_account = await accounts_store.get_account_by_name(
        payload.budget_id, payload.name
    )
    if existing_account is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account name already exists.",
        )

    return await accounts_store.create_account(
        budget_id=payload.budget_id,
        name=payload.name,
        type=payload.type,
        currency_code=currency_code,
        is_closed=payload.is_closed,
    )


@router.get("/budgets/{budget_id}/accounts", response_model=list[AccountResponse])
async def list_accounts(
    budget_id: uuid.UUID,
    accounts_store: AccountsDataAccess = Depends(),
    budgets_store: BudgetsDataAccess = Depends(),
) -> list[Account]:
    budget = await budgets_store.get_budget(budget_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found.",
        )

    return await accounts_store.list_accounts(budget_id)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    accounts_store: AccountsDataAccess = Depends(),
    currencies_store: CurrenciesDataAccess = Depends(),
) -> Account:
    account = await accounts_store.get_account(account_id)
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
        currency = await currencies_store.get_currency(currency_code)
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown currency code.",
            )

    if "name" in updates:
        existing_account = await accounts_store.get_account_by_name(
            account.budget_id,
            updates["name"],
            exclude_account_id=account.id,
        )
        if existing_account is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account name already exists.",
            )

    if "currency_code" in updates:
        updates["currency_code"] = currency_code

    updated_account = await accounts_store.update_account(account_id, updates)
    if updated_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )
    return updated_account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    accounts_store: AccountsDataAccess = Depends(),
) -> None:
    deleted = await accounts_store.delete(account_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )
