from datetime import datetime
from uuid import UUID

from httpx import ASGITransport, AsyncClient

TEST_USER_ID = UUID("74f8e448-a061-70f2-64ce-b7a19aa3ed8a")
TEST_USER_EMAIL = "masonflint44@gmail.com"


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    return datetime.fromisoformat(value)


async def test_get_current_user_profile_returns_authenticated_user(async_client) -> None:
    response = await async_client.get("/users/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(TEST_USER_ID)
    assert payload["email"] == TEST_USER_EMAIL
    assert "created_at" in payload
    assert "last_seen_at" in payload


async def test_get_current_user_profile_last_seen_is_timezone_aware(async_client) -> None:
    response = await async_client.get("/users/me")

    assert response.status_code == 200
    payload = response.json()

    created_at = _parse_iso_datetime(payload["created_at"])
    last_seen_at = _parse_iso_datetime(payload["last_seen_at"])

    assert created_at.tzinfo is not None
    assert last_seen_at.tzinfo is not None


async def test_get_current_user_profile_rejects_unauthenticated_request(app) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as unauthenticated_client:
        response = await unauthenticated_client.get("/users/me")

    assert response.status_code == 401
