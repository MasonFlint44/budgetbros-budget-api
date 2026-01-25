from uuid import UUID

from budget_api.tables import BudgetsTable
from tests.conftest import get_test_db_session


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

    async with get_test_db_session() as session:
        budget = await session.get(BudgetsTable, budget_id)

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

    async with get_test_db_session() as session:
        budget = await session.get(BudgetsTable, UUID(budget_id))

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

    async with get_test_db_session() as session:
        budget = await session.get(BudgetsTable, UUID(budget_id))

        assert budget is None


async def test_list_budgets_empty(app, async_client, seeded_currencies) -> None:
    response = await async_client.get("/budgets")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_budgets_ordered_by_created_at(
    app, async_client, seeded_currencies
) -> None:
    first_response = await async_client.post(
        "/budgets", json={"name": "Alpha", "base_currency_code": "USD"}
    )
    second_response = await async_client.post(
        "/budgets", json={"name": "Beta", "base_currency_code": "EUR"}
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get("/budgets")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta"]


async def test_create_budget_rejects_unknown_currency(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "ZZZ"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown base currency code."


async def test_create_budget_validates_payload(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "", "base_currency_code": "US"}
    )

    assert response.status_code == 422


async def test_create_budget_normalizes_currency_code(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "usd"}
    )

    assert response.status_code == 201
    assert response.json()["base_currency_code"] == "USD"


async def test_update_budget_rejects_unknown_currency(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"base_currency_code": "ZZZ"}
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Unknown base currency code."


async def test_update_budget_requires_fields(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(f"/budgets/{budget_id}", json={})

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "No fields to update."


async def test_update_budget_validates_payload(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"name": "", "base_currency_code": "US"}
    )

    assert update_response.status_code == 422


async def test_update_budget_not_found(app, async_client, seeded_currencies) -> None:
    update_response = await async_client.patch(
        "/budgets/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Budget not found."


async def test_update_budget_invalid_id(app, async_client, seeded_currencies) -> None:
    update_response = await async_client.patch(
        "/budgets/not-a-uuid", json={"name": "Updated"}
    )

    assert update_response.status_code == 422


async def test_update_budget_normalizes_currency_code(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"base_currency_code": "eur"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["base_currency_code"] == "EUR"


async def test_delete_budget_not_found(app, async_client, seeded_currencies) -> None:
    delete_response = await async_client.delete(
        "/budgets/00000000-0000-0000-0000-000000000000"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Budget not found."


async def test_delete_budget_invalid_id(app, async_client, seeded_currencies) -> None:
    delete_response = await async_client.delete("/budgets/not-a-uuid")

    assert delete_response.status_code == 422


async def test_delete_budget_has_empty_body(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    delete_response = await async_client.delete(f"/budgets/{budget_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
