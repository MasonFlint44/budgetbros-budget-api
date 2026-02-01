import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from budget_api.auth import get_or_create_current_user
from budget_api.models import Account, AccountCreate, AccountResponse, AccountUpdate, User
from budget_api.services import AccountsService

router = APIRouter(prefix="/budgets/{budget_id}/accounts")


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    budget_id: uuid.UUID,
    payload: AccountCreate,
    current_user: User = Depends(get_or_create_current_user),
    accounts_service: AccountsService = Depends(),
) -> Account:
    return await accounts_service.create_account(
        budget_id=budget_id,
        name=payload.name,
        type=payload.type,
        currency_code=payload.currency_code,
        is_active=payload.is_active,
        user_id=current_user.id,
    )


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_or_create_current_user),
    accounts_service: AccountsService = Depends(),
) -> list[Account]:
    return await accounts_service.list_accounts(budget_id, current_user.id)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    budget_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: User = Depends(get_or_create_current_user),
    accounts_service: AccountsService = Depends(),
) -> Account:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    return await accounts_service.update_account(
        budget_id, account_id, updates, current_user.id
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    budget_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: User = Depends(get_or_create_current_user),
    accounts_service: AccountsService = Depends(),
) -> None:
    await accounts_service.delete_account(budget_id, account_id, current_user.id)
