from contextlib import asynccontextmanager

from fastapi import FastAPI

from budget_api import db
from budget_api.routers import budgets

@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(budgets.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}

