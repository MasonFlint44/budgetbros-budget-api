from fastapi import APIRouter, Depends

from budget_api.models import Currency, CurrencyResponse
from budget_api.services import CurrenciesService

router = APIRouter(prefix="/currencies")


@router.get("", response_model=list[CurrencyResponse])
async def list_currencies(
    currencies_service: CurrenciesService = Depends(),
) -> list[Currency]:
    return await currencies_service.list_currencies()
