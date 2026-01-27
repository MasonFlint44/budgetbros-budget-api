from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException

from budget_api.auth import get_or_create_current_user
from budget_api.tables import UsersTable
from tests.conftest import TEST_AUTH_TOKEN
from budget_api.db import get_session_scope

TEST_USER_ID = UUID("74f8e448-a061-70f2-64ce-b7a19aa3ed8a")
TEST_USER_EMAIL = "masonflint44@gmail.com"


async def test_get_or_create_current_user_creates_user() -> None:
    async with get_session_scope() as session:
        user = await get_or_create_current_user(token=TEST_AUTH_TOKEN, session=session)

        assert user.id == TEST_USER_ID
        assert user.email == TEST_USER_EMAIL

        db_user = await session.get(UsersTable, TEST_USER_ID)
        assert db_user is not None
        assert db_user.email == TEST_USER_EMAIL
        assert db_user.last_seen_at >= db_user.created_at


async def test_get_or_create_current_user_updates_last_seen() -> None:
    old_seen = datetime.now(timezone.utc) - timedelta(days=1)

    async with get_session_scope() as session:
        existing = await session.get(UsersTable, TEST_USER_ID)
        if existing is None:
            existing = UsersTable(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                created_at=old_seen,
                last_seen_at=old_seen,
            )
            session.add(existing)
        else:
            existing.created_at = old_seen
            existing.last_seen_at = old_seen
        await session.flush()

        user = await get_or_create_current_user(token=TEST_AUTH_TOKEN, session=session)
        await session.refresh(existing)

        assert user.id == TEST_USER_ID
        assert existing.created_at == old_seen
        assert existing.last_seen_at > old_seen


async def test_get_or_create_current_user_rejects_invalid_token() -> None:
    async with get_session_scope() as session:
        with pytest.raises(HTTPException) as exc:
            await get_or_create_current_user(token="not-a-token", session=session)

    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


def test_app_dependencies_include_get_or_create_current_user(app) -> None:
    dependency_functions = {dep.dependency for dep in app.router.dependencies}
    assert get_or_create_current_user in dependency_functions
