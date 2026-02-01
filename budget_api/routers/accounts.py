import uuid

from fastapi import APIRouter, Depends, status

from budget_api.dependencies import require_budget_member
from budget_api.models import Account, AccountCreate, AccountResponse, AccountUpdate, Budget
from budget_api.routers.utils import extract_updates
from budget_api.services import AccountsService

router = APIRouter(prefix="/budgets/{budget_id}/accounts")


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage accounts.")),
    accounts_service: AccountsService = Depends(),
) -> Account:
    return await accounts_service.create_account(
        budget=budget,
        name=payload.name,
        type=payload.type,
        currency_code=payload.currency_code,
        is_active=payload.is_active,
    )


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    budget: Budget = Depends(require_budget_member("Not authorized to view accounts.")),
    accounts_service: AccountsService = Depends(),
) -> list[Account]:
    return await accounts_service.list_accounts(budget)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage accounts.")),
    accounts_service: AccountsService = Depends(),
) -> Account:
    updates = extract_updates(payload)
    return await accounts_service.update_account(budget, account_id, updates)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to manage accounts.")),
    accounts_service: AccountsService = Depends(),
) -> None:
    await accounts_service.delete_account(budget, account_id)
