import uuid

from fastapi import APIRouter, Depends, status

from budget_api.auth import get_or_create_current_user
from budget_api.models import Transaction, TransactionCreate, TransactionResponse, User
from budget_api.services import TransactionsService

router = APIRouter(prefix="/budgets/{budget_id}/transactions")


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    budget_id: uuid.UUID,
    payload: TransactionCreate,
    current_user: User = Depends(get_or_create_current_user),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.create_transaction(
        budget_id=budget_id,
        payload=payload,
        user_id=current_user.id,
    )
