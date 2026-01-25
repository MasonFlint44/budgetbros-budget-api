from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Account, AccountType
from budget_api.tables import AccountsTable


class AccountsDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_account(self, account_id: uuid.UUID) -> Account | None:
        account = await self._session.get(AccountsTable, account_id)
        if account is None:
            return None
        return _to_account(account)

    async def get_account_by_name(
        self,
        budget_id: uuid.UUID,
        name: str,
        *,
        exclude_account_id: uuid.UUID | None = None,
    ) -> Account | None:
        statement = select(AccountsTable).where(
            AccountsTable.budget_id == budget_id,
            AccountsTable.name == name,
        )
        if exclude_account_id is not None:
            statement = statement.where(AccountsTable.id != exclude_account_id)
        result = await self._session.execute(statement)
        account = result.scalar_one_or_none()
        if account is None:
            return None
        return _to_account(account)

    async def list_accounts(self, budget_id: uuid.UUID) -> list[Account]:
        result = await self._session.execute(
            select(AccountsTable)
            .where(AccountsTable.budget_id == budget_id)
            .order_by(AccountsTable.created_at)
        )
        return [_to_account(account) for account in result.scalars()]

    async def create_account(
        self,
        *,
        budget_id: uuid.UUID,
        name: str,
        type: str,
        currency_code: str,
        is_closed: bool,
    ) -> Account:
        account = AccountsTable(
            budget_id=budget_id,
            name=name,
            type=type,
            currency_code=currency_code,
            is_closed=is_closed,
        )
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return _to_account(account)

    async def update_account(
        self, account_id: uuid.UUID, updates: dict[str, object]
    ) -> Account | None:
        account = await self._session.get(AccountsTable, account_id)
        if account is None:
            return None
        for field, value in updates.items():
            setattr(account, field, value)
        await self._session.flush()
        await self._session.refresh(account)
        return _to_account(account)

    async def delete(self, account_id: uuid.UUID) -> bool:
        account = await self._session.get(AccountsTable, account_id)
        if account is None:
            return False
        await self._session.delete(account)
        await self._session.flush()
        return True


def _to_account(account: AccountsTable) -> Account:
    return Account(
        id=account.id,
        budget_id=account.budget_id,
        name=account.name,
        type=AccountType(account.type),
        currency_code=account.currency_code,
        is_closed=account.is_closed,
        created_at=account.created_at,
    )
