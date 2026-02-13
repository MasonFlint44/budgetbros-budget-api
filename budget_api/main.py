from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from budget_api import db
from budget_api.auth import verifier, get_or_create_current_user
from budget_api.routers import (
    accounts,
    budgets,
    categories,
    currencies,
    payees,
    transactions,
)
from budget_api.data_access import CurrenciesDataAccess
from budget_api.data import CURRENCIES


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    async with db.get_session_scope() as session:
        currencies_store = CurrenciesDataAccess(session)
        await currencies_store.seed_currencies(CURRENCIES)
    await verifier.init_keys()
    yield
    await verifier.close()


app = FastAPI(
    title="BudgetBros - Budget API",
    dependencies=[Depends(get_or_create_current_user)],
    lifespan=lifespan,
)
app.include_router(budgets.router, tags=["budgets"])
app.include_router(accounts.router, tags=["accounts"])
app.include_router(categories.router, tags=["categories"])
app.include_router(payees.router, tags=["payees"])
app.include_router(currencies.router, tags=["currencies"])
app.include_router(transactions.router, tags=["transactions"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
