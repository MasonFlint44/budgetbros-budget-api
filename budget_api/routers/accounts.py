import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.models import Account, AccountCreate, AccountResponse, AccountUpdate
from budget_api.services import AccountsService

router = APIRouter()


@router.post(
    "/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_account(
    payload: AccountCreate,
    accounts_service: AccountsService = Depends(),
) -> Account:
    return await accounts_service.create_account(
        budget_id=payload.budget_id,
        name=payload.name,
        type=payload.type,
        currency_code=payload.currency_code,
        is_closed=payload.is_closed,
    )


@router.get("/budgets/{budget_id}/accounts", response_model=list[AccountResponse])
async def list_accounts(
    budget_id: uuid.UUID,
    accounts_service: AccountsService = Depends(),
) -> list[Account]:
    return await accounts_service.list_accounts(budget_id)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    accounts_service: AccountsService = Depends(),
) -> Account:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    return await accounts_service.update_account(account_id, updates)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    accounts_service: AccountsService = Depends(),
) -> None:
    await accounts_service.delete_account(account_id)
