from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import PayeesDataAccess
from budget_api.models import Budget, Payee


class PayeesService:
    def __init__(
        self,
        payees_store: PayeesDataAccess = Depends(),
    ) -> None:
        self._payees_store = payees_store

    async def _require_budget_payee(self, budget: Budget, payee_id: uuid.UUID) -> Payee:
        payee = await self._payees_store.get_payee(payee_id)
        if payee is None or payee.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payee not found.",
            )
        return payee

    async def create_payee(
        self,
        *,
        budget: Budget,
        name: str,
    ) -> Payee:
        existing_payee = await self._payees_store.get_payee_by_name(budget.id, name)
        if existing_payee is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payee name already exists.",
            )

        return await self._payees_store.create_payee(
            budget_id=budget.id,
            name=name,
        )

    async def list_payees(self, budget: Budget) -> list[Payee]:
        return await self._payees_store.list_payees_by_budget(budget.id)

    async def get_payee(self, budget: Budget, payee_id: uuid.UUID) -> Payee:
        return await self._require_budget_payee(budget, payee_id)

    async def update_payee(
        self,
        budget: Budget,
        payee_id: uuid.UUID,
        updates: dict[str, object],
    ) -> Payee:
        payee = await self._require_budget_payee(budget, payee_id)

        if "name" in updates:
            existing_payee = await self._payees_store.get_payee_by_name(
                budget.id,
                str(updates["name"]),
                exclude_payee_id=payee.id,
            )
            if existing_payee is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Payee name already exists.",
                )

        updated_payee = await self._payees_store.update_payee(payee.id, updates)
        if updated_payee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payee not found.",
            )
        return updated_payee

    async def delete_payee(self, budget: Budget, payee_id: uuid.UUID) -> None:
        await self._require_budget_payee(budget, payee_id)
        deleted = await self._payees_store.delete_payee(payee_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payee not found.",
            )
