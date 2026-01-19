from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import BudgetCreate, BudgetResponse
from budget_api.tables import Budget, Currency

@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate, session: AsyncSession = Depends(db.get_session)
) -> Budget:
    currency_code = payload.base_currency_code.upper()
    result = await session.execute(
        select(Currency).where(Currency.code == currency_code)
    )
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown base currency code.",
        )
    budget = Budget(name=payload.name, base_currency_code=currency_code)
    session.add(budget)
    await session.flush()
    await session.refresh(budget)
    return budget
