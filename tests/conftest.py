import os
from contextlib import asynccontextmanager

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from budget_api import db
from budget_api.auth import verifier
from budget_api.main import app as fastapi_app
from budget_api.tables import Base, CurrenciesTable

TEST_AUTH_TOKEN = "eyJraWQiOiIwQ25KQVE4VllsNnVDZjA5eXpUWVdlUFZVdm5vNnpVUUZsUU5kSlpJMXJVPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI3NGY4ZTQ0OC1hMDYxLTcwZjItNjRjZS1iN2ExOWFhM2VkOGEiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9McWlSWWQxRkQiLCJjbGllbnRfaWQiOiI1NTVlcGwxOWVwajlpMGVyYXQ3NmM0NDgwMyIsIm9yaWdpbl9qdGkiOiJhOTZlMDRjNi00ZjQ0LTQ2ZjItOTlkMC1mZGYzYWM5Y2U0MDMiLCJldmVudF9pZCI6ImM3YjcyMTE5LTFlYWQtNDAzNy04ZjViLTVmZmU4NjFmMDc5NyIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE3NjkyODU0ODksImV4cCI6MTc2OTI4OTA4OSwiaWF0IjoxNzY5Mjg1NDg5LCJlbWFpbCI6Im1hc29uZmxpbnQ0NEBnbWFpbC5jb20iLCJqdGkiOiJlM2IzYjIzMy1jNzg4LTQ1MDctODUxYy0xZmM2NmMwNmIwMTgiLCJ1c2VybmFtZSI6Ijc0ZjhlNDQ4LWEwNjEtNzBmMi02NGNlLWI3YTE5YWEzZWQ4YSJ9.PttfiXBEyWE2yAIzEmE9IJkkREl7f2uKuI2WzhztV7X-8Js7VfOs2c9Heu_hguYO7vMQ1qO0ieHkN7UhikWx8pI_eJnUm4AzTYSDM2-XSloOVDsauAv6TSa5buIhayH5H6rrA_4bslBiAKVtsJH5tqMagEJoAHydI2W19q98Beaz1TAxIYwTulbLuWxlzjXpoEQ7pjJhSOakIQ2e_bSQ0pg3Gnd-foiPZyZXz9i17sm-OG8biY6nzbQICky4Ek4rPhO6rJK7zq0L3OMPEOkCkcgZT4bOtEykHzHFNTkZvqQJ-MllgZ2fSzS4fjmHWR2fqYe2T_78vykjfRE8Th5B9A"  # pylint: disable=line-too-long


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():
    return ("asyncio", {"use_uvloop": True})


@pytest.fixture(scope="session")
def app():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set for postgres-backed tests.")
    db.reset_engine()
    return fastapi_app


@pytest.fixture(autouse=True)
def override_verifier_expiry():
    original_verify = verifier.verify_access_token
    verifier.verify_access_token = (
        verifier._verify_access_token_allow_expired # pylint: disable=protected-access
    )
    yield
    verifier.verify_access_token = original_verify


@pytest.fixture(autouse=True, scope="session")
async def db_schema():
    engine = db.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="session")
async def async_client(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {TEST_AUTH_TOKEN}"},
        ) as client:
            yield client


@asynccontextmanager
async def get_test_db_session():
    session_generator = db.get_session()
    session = await anext(session_generator)
    try:
        yield session
    finally:
        try:
            await anext(session_generator)
        except StopAsyncIteration:
            pass


@pytest.fixture(scope="session")
async def seeded_currencies(async_client):
    async with get_test_db_session() as session:
        session.add_all(
            [
                CurrenciesTable(code="USD", name="US Dollar", symbol="$", minor_unit=2),
                CurrenciesTable(code="EUR", name="Euro", symbol="EUR", minor_unit=2),
            ]
        )
