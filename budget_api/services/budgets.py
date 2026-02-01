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
        self, budget_id: uuid.UUID, updates: dict[str, object], user_id: uuid.UUID
    ) -> Budget:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        is_member = await self._budgets_store.budget_member_exists(budget_id, user_id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update budget.",
            )

        if "base_currency_code" in updates:
            currency_code = str(updates["base_currency_code"]).upper()
            currency = await self._currencies_store.get_currency(currency_code)
            if currency is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown base currency code.",
                )
            if currency_code != budget.base_currency_code:
                await self._accounts_store.deactivate_accounts_by_budget(budget_id)
            updates["base_currency_code"] = currency_code

        updated_budget = await self._budgets_store.update_budget(budget_id, updates)
        if updated_budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        return updated_budget

    async def delete_budget(self, budget_id: uuid.UUID, user_id: uuid.UUID) -> None:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )
        is_owner = await self._budgets_store.budget_owner_exists(budget_id, user_id)
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete budget.",
            )
        deleted = await self._budgets_store.delete(budget_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

    async def add_budget_member(
        self,
        budget_id: uuid.UUID,
        member_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

        is_owner = await self._budgets_store.budget_owner_exists(
            budget_id, current_user_id
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to manage budget members.",
            )

        user_exists = await self._budgets_store.user_exists(member_user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        member_exists = await self._budgets_store.budget_member_exists(
            budget_id, member_user_id
        )
        if member_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already belongs to budget.",
            )

        await self._budgets_store.add_budget_member(
            budget_id=budget_id, user_id=member_user_id
        )

    async def remove_budget_member(
        self,
        budget_id: uuid.UUID,
        member_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

        is_owner = await self._budgets_store.budget_owner_exists(
            budget_id, current_user_id
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to manage budget members.",
            )

        deleted = await self._budgets_store.remove_budget_member(
            budget_id, member_user_id
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget member not found.",
            )

    async def list_budget_members(
        self, budget_id: uuid.UUID, current_user_id: uuid.UUID
    ) -> list[BudgetMember]:
        budget = await self._budgets_store.get_budget(budget_id)
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found.",
            )

        is_member = await self._budgets_store.budget_member_exists(
            budget_id, current_user_id
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view budget members.",
            )

        return await self._budgets_store.list_budget_members(budget_id)
