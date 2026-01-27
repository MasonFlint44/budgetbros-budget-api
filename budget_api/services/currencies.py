from __future__ import annotations

from fastapi import Depends

from budget_api.data_access import CurrenciesDataAccess
from budget_api.models import Currency


class CurrenciesService:
    def __init__(self, currencies_store: CurrenciesDataAccess = Depends()) -> None:
        self._currencies_store = currencies_store

    async def list_currencies(self) -> list[Currency]:
        return await self._currencies_store.list_currencies()
