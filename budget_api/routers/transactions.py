import uuid

from fastapi import APIRouter, Depends, status

from budget_api.dependencies import require_budget_member
from budget_api.models import (
    Budget,
    Transaction,
    TransactionCreate,
    TransactionResponse,
    TransactionSplitCreate,
    TransactionUpdate,
    TransferCreate,
)
from budget_api.services import TransactionsService

router = APIRouter(prefix="/budgets/{budget_id}/transactions")


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to create transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.create_transaction(
        budget_id=budget.id,
        payload=payload,
    )


@router.post(
    "/transfer", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transfer(
    payload: TransferCreate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to create transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.create_transfer(
        budget=budget,
        payload=payload,
    )


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    include_lines: bool = True,
    budget: Budget = Depends(
        require_budget_member("Not authorized to view transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> list[Transaction]:
    return await transactions_service.list_transactions(
        budget.id, include_lines=include_lines
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    include_lines: bool = True,
    budget: Budget = Depends(
        require_budget_member("Not authorized to view transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.get_transaction(
        budget.id,
        transaction_id,
        include_lines=include_lines,
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to update transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.update_transaction(
        budget_id=budget.id,
        transaction_id=transaction_id,
        payload=payload,
    )


@router.post("/{transaction_id}/split", response_model=TransactionResponse)
async def split_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionSplitCreate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to update transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> Transaction:
    return await transactions_service.split_transaction(
        budget_id=budget.id,
        transaction_id=transaction_id,
        payload=payload,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    budget: Budget = Depends(
        require_budget_member("Not authorized to delete transactions.")
    ),
    transactions_service: TransactionsService = Depends(),
) -> None:
    await transactions_service.delete_transaction(
        budget_id=budget.id,
        transaction_id=transaction_id,
    )
