from contextlib import asynccontextmanager

import os
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from budget_api import db
from budget_api.main import app as fastapi_app
from budget_api.tables import Base, Currency


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():
    return ("asyncio", {"use_uvloop": True})


@pytest.fixture
def app():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set for postgres-backed tests.")
    db.reset_engine()
    return fastapi_app


@pytest.fixture(autouse=True)
async def db_schema(app):
    engine = db.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture
async def async_client(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@asynccontextmanager
async def get_test_session():
    session_generator = db.get_session()
    session = await anext(session_generator)
    try:
        yield session
    finally:
        try:
            await anext(session_generator)
        except StopAsyncIteration:
            pass


@pytest.fixture
async def seeded_currencies(async_client):
    async with get_test_session() as session:
        session.add_all(
            [
                Currency(code="USD", name="US Dollar", symbol="$", minor_unit=2),
                Currency(code="EUR", name="Euro", symbol="EUR", minor_unit=2),
            ]
        )
