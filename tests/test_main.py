from uuid import UUID

from budget_api.tables import Budget
from tests.conftest import get_test_session


async def test_create_budget(app, async_client, seeded_currencies) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Household"
    assert payload["base_currency_code"] == "USD"
    assert "id" in payload
    assert "created_at" in payload


async def test_budget_persists_in_db(app, async_client, seeded_currencies) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])

    async with get_test_session() as session:
        budget = await session.get(Budget, budget_id)

        assert budget is not None
        assert budget.name == "Household"
        assert budget.base_currency_code == "USD"
