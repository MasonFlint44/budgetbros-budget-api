from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects.postgresql import insert

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

    async def seed_currencies(self, currencies: list[CurrenciesTable]) -> None:
        rows = [
            {attr.key: getattr(c, attr.key) for attr in inspect(c).mapper.column_attrs}
            for c in currencies
        ]
        stmt = insert(CurrenciesTable).values(rows)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[CurrenciesTable.code],
            set_={
                "code": stmt.excluded.code,
                "name": stmt.excluded.name,
                "symbol": stmt.excluded.symbol,
                "minor_unit": stmt.excluded.minor_unit,
            },
        )
        await self._session.execute(upsert_stmt)
        await self._session.commit()


def _to_currency(currency: CurrenciesTable) -> Currency:
    return Currency(
        code=currency.code,
        name=currency.name,
        symbol=currency.symbol,
        minor_unit=currency.minor_unit,
    )
