from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from budget_api.data_access import AccountsDataAccess, CurrenciesDataAccess
from budget_api.models import Account, Budget


class AccountsService:
    def __init__(
        self,
        accounts_store: AccountsDataAccess = Depends(),
        currencies_store: CurrenciesDataAccess = Depends(),
    ) -> None:
        self._accounts_store = accounts_store
        self._currencies_store = currencies_store

    async def create_account(
        self,
        *,
        budget: Budget,
        name: str,
        type: str,
        currency_code: str,
        is_active: bool,
    ) -> Account:
        normalized_currency_code = currency_code.upper()
        currency = await self._currencies_store.get_currency(normalized_currency_code)
        if currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown currency code.",
            )
        if normalized_currency_code != budget.base_currency_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account currency must match budget base currency.",
            )

        existing_account = await self._accounts_store.get_account_by_name(
            budget.id, name
        )
        if existing_account is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account name already exists.",
            )

        return await self._accounts_store.create_account(
            budget_id=budget.id,
            name=name,
            type=type,
            currency_code=normalized_currency_code,
            is_active=is_active,
        )

    async def list_accounts(
        self, budget: Budget
    ) -> list[Account]:
        return await self._accounts_store.list_accounts_by_budget(budget.id)

    async def update_account(
        self,
        budget: Budget,
        account_id: uuid.UUID,
        updates: dict[str, object],
    ) -> Account:
        account = await self._accounts_store.get_account(account_id)
        if account is None or account.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        if "currency_code" in updates:
            currency_code = str(updates["currency_code"]).upper()
            currency = await self._currencies_store.get_currency(currency_code)
            if currency is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown currency code.",
                )
            if currency_code != budget.base_currency_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account currency must match budget base currency.",
                )
            updates["currency_code"] = currency_code
        elif account.currency_code != budget.base_currency_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account currency must match budget base currency.",
            )

        if "name" in updates:
            existing_account = await self._accounts_store.get_account_by_name(
                account.budget_id,
                str(updates["name"]),
                exclude_account_id=account.id,
            )
            if existing_account is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account name already exists.",
                )

        updated_account = await self._accounts_store.update_account(account_id, updates)
        if updated_account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )
        return updated_account

    async def delete_account(
        self, budget: Budget, account_id: uuid.UUID
    ) -> None:
        account = await self._accounts_store.get_account(account_id)
        if account is None or account.budget_id != budget.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )
        deleted = await self._accounts_store.delete(account_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )
