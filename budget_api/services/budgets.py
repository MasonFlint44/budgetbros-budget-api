from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import BudgetsDataAccess, CurrenciesDataAccess
from budget_api.models import Budget


class BudgetsService:
    def __init__(
        self,
        budgets_store: BudgetsDataAccess = Depends(),
        currencies_store: CurrenciesDataAccess = Depends(),
    ) -> None:
        self._budgets_store = budgets_store
        self._currencies_store = currencies_store

    async def create_budget(self, name: str, base_currency_code: str) -> Budget:
        currency_code = base_currency_code.upper()
        currency = await self._currencies_store.get_currency(currency_code)
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown base currency code.",
            )
        return await self._budgets_store.create_budget(
            name=name, base_currency_code=currency_code
        )

    async def list_budgets(self) -> list[Budget]:
        return await self._budgets_store.list_budgets()

    async def update_budget(
        self, budget_id: uuid.UUID, updates: dict[str, object]
    ) -> Budget:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

        if "base_currency_code" in updates:
            currency_code = str(updates["base_currency_code"]).upper()
            currency = await self._currencies_store.get_currency(currency_code)
            if currency is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown base currency code.",
                )
            updates["base_currency_code"] = currency_code

        updated_budget = await self._budgets_store.update_budget(budget_id, updates)
        if updated_budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        return updated_budget

    async def delete_budget(self, budget_id: uuid.UUID) -> None:
        deleted = await self._budgets_store.delete(budget_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
