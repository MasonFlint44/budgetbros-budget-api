from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import (
    AccountsDataAccess,
    BudgetsDataAccess,
    CurrenciesDataAccess,
)
from budget_api.models import Budget, BudgetMember


class BudgetsService:
    def __init__(
        self,
        budgets_store: BudgetsDataAccess = Depends(),
        currencies_store: CurrenciesDataAccess = Depends(),
        accounts_store: AccountsDataAccess = Depends(),
    ) -> None:
        self._budgets_store = budgets_store
        self._currencies_store = currencies_store
        self._accounts_store = accounts_store

    async def create_budget(
        self, name: str, base_currency_code: str, owner_user_id: uuid.UUID
    ) -> Budget:
        currency_code = base_currency_code.upper()
        currency = await self._currencies_store.get_currency(currency_code)
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown base currency code.",
            )
        budget = await self._budgets_store.create_budget(
            name=name,
            base_currency_code=currency_code,
            owner_user_id=owner_user_id,
        )
        await self._budgets_store.add_budget_member(
            budget_id=budget.id, user_id=owner_user_id
        )
        return budget

    async def list_budgets(self, user_id: uuid.UUID) -> list[Budget]:
        return await self._budgets_store.list_budgets_for_user(user_id)

    async def update_budget(
        self, budget: Budget, updates: dict[str, object]
    ) -> Budget:
        if "base_currency_code" in updates:
            currency_code = str(updates["base_currency_code"]).upper()
            currency = await self._currencies_store.get_currency(currency_code)
            if currency is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown base currency code.",
                )
            if currency_code != budget.base_currency_code:
                await self._accounts_store.deactivate_accounts_by_budget(budget.id)
            updates["base_currency_code"] = currency_code

        updated_budget = await self._budgets_store.update_budget(budget.id, updates)
        if updated_budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        return updated_budget

    async def delete_budget(self, budget: Budget) -> None:
        deleted = await self._budgets_store.delete(budget.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

    async def add_budget_member(
        self,
        budget: Budget,
        member_user_id: uuid.UUID,
    ) -> None:
        user_exists = await self._budgets_store.user_exists(member_user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        member_exists = await self._budgets_store.budget_member_exists(
            budget.id, member_user_id
        )
        if member_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already belongs to budget.",
            )

        await self._budgets_store.add_budget_member(
            budget_id=budget.id, user_id=member_user_id
        )

    async def remove_budget_member(
        self,
        budget: Budget,
        member_user_id: uuid.UUID,
    ) -> None:
        deleted = await self._budgets_store.remove_budget_member(
            budget.id, member_user_id
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget member not found.",
            )

    async def list_budget_members(
        self, budget: Budget
    ) -> list[BudgetMember]:
        return await self._budgets_store.list_budget_members(budget.id)
