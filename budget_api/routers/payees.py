import uuid

from fastapi import APIRouter, Depends, status

from budget_api.dependencies import require_budget_member
from budget_api.models import Budget, Payee, PayeeCreate, PayeeResponse, PayeeUpdate
from budget_api.routers.utils import extract_updates
from budget_api.services import PayeesService

router = APIRouter(prefix="/budgets/{budget_id}/payees")


@router.post("", response_model=PayeeResponse, status_code=status.HTTP_201_CREATED)
async def create_payee(
    payload: PayeeCreate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage payees.")),
    payees_service: PayeesService = Depends(),
) -> Payee:
    return await payees_service.create_payee(
        budget=budget,
        name=payload.name,
    )


@router.get("", response_model=list[PayeeResponse])
async def list_payees(
    budget: Budget = Depends(require_budget_member("Not authorized to view payees.")),
    payees_service: PayeesService = Depends(),
) -> list[Payee]:
    return await payees_service.list_payees(budget)


@router.get("/{payee_id}", response_model=PayeeResponse)
async def get_payee(
    payee_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to view payees.")),
    payees_service: PayeesService = Depends(),
) -> Payee:
    return await payees_service.get_payee(budget, payee_id)


@router.patch("/{payee_id}", response_model=PayeeResponse)
async def update_payee(
    payee_id: uuid.UUID,
    payload: PayeeUpdate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage payees.")),
    payees_service: PayeesService = Depends(),
) -> Payee:
    updates = extract_updates(payload)
    return await payees_service.update_payee(budget, payee_id, updates)


@router.delete("/{payee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payee(
    payee_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to manage payees.")),
    payees_service: PayeesService = Depends(),
) -> None:
    await payees_service.delete_payee(budget, payee_id)
