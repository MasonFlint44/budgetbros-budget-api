from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import Currency
from budget_api.tables import CurrenciesTable


class CurrenciesDataAccess:
    def __init__(self, session: AsyncSession = Depends(db.get_session)) -> None:
        self._session = session

    async def get_currency(self, code: str) -> Currency | None:
        result = await self._session.execute(
            select(CurrenciesTable).where(CurrenciesTable.code == code)
        )
        currency = result.scalar_one_or_none()
        if currency is None:
            return None
        return _to_currency(currency)

    async def list_currencies(self) -> list[Currency]:
        result = await self._session.execute(
            select(CurrenciesTable).order_by(CurrenciesTable.code)
        )
        return [_to_currency(currency) for currency in result.scalars()]


def _to_currency(currency: CurrenciesTable) -> Currency:
    return Currency(
        code=currency.code,
        name=currency.name,
        symbol=currency.symbol,
        minor_unit=currency.minor_unit,
    )
