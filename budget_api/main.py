from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from budget_api import db
from budget_api.auth import verifier, get_or_create_current_user
from budget_api.routers import accounts, budgets


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
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


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}
