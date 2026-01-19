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


async def test_list_budgets(app, async_client, seeded_currencies) -> None:
    first_response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    second_response = await async_client.post(
        "/budgets", json={"name": "Vacation", "base_currency_code": "EUR"}
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get("/budgets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["name"] == "Household"
    assert payload[1]["name"] == "Vacation"
    assert payload[0]["base_currency_code"] == "USD"
    assert payload[1]["base_currency_code"] == "EUR"
    assert "id" in payload[0]
    assert "created_at" in payload[0]


async def test_update_budget(app, async_client, seeded_currencies) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}",
        json={"name": "Updated", "base_currency_code": "EUR"},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == budget_id
    assert payload["name"] == "Updated"
    assert payload["base_currency_code"] == "EUR"

    async with get_test_session() as session:
        budget = await session.get(Budget, UUID(budget_id))

        assert budget is not None
        assert budget.name == "Updated"
        assert budget.base_currency_code == "EUR"


async def test_delete_budget(app, async_client, seeded_currencies) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = response.json()["id"]

    delete_response = await async_client.delete(f"/budgets/{budget_id}")

    assert delete_response.status_code == 204

    async with get_test_session() as session:
        budget = await session.get(Budget, UUID(budget_id))

        assert budget is None
