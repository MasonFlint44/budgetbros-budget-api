from uuid import UUID

from budget_api.tables import Account
from tests.conftest import get_test_session


async def create_budget(async_client) -> str:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_account(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Checking"
    assert payload["type"] == "checking"
    assert payload["currency_code"] == "USD"
    assert payload["is_closed"] is False
    assert "id" in payload
    assert "created_at" in payload


async def test_account_persists_in_db(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = UUID(response.json()["id"])

    async with get_test_session() as session:
        account = await session.get(Account, account_id)

        assert account is not None
        assert account.name == "Checking"
        assert account.type == "checking"
        assert account.currency_code == "USD"
        assert account.is_closed is False


async def test_list_accounts(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Savings",
            "type": "savings",
            "currency_code": "EUR",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/accounts")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["name"] == "Checking"
    assert payload[1]["name"] == "Savings"
    assert payload[0]["currency_code"] == "USD"
    assert payload[1]["currency_code"] == "EUR"
    assert "id" in payload[0]
    assert "created_at" in payload[0]


async def test_update_account(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/accounts/{account_id}",
        json={
            "name": "Updated",
            "type": "savings",
            "currency_code": "EUR",
            "is_closed": True,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == account_id
    assert payload["name"] == "Updated"
    assert payload["type"] == "savings"
    assert payload["currency_code"] == "EUR"
    assert payload["is_closed"] is True

    async with get_test_session() as session:
        account = await session.get(Account, UUID(account_id))

        assert account is not None
        assert account.name == "Updated"
        assert account.type == "savings"
        assert account.currency_code == "EUR"
        assert account.is_closed is True


async def test_delete_account(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = response.json()["id"]

    delete_response = await async_client.delete(f"/accounts/{account_id}")

    assert delete_response.status_code == 204

    async with get_test_session() as session:
        account = await session.get(Account, UUID(account_id))

        assert account is None


async def test_list_accounts_empty(app, async_client, seeded_currencies) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.get(f"/budgets/{budget_id}/accounts")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_accounts_ordered_by_created_at(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Alpha",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Beta",
            "type": "checking",
            "currency_code": "EUR",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/accounts")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta"]


async def test_create_account_rejects_unknown_currency(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "ZZZ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown currency code."


async def test_create_account_rejects_unknown_budget(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": "00000000-0000-0000-0000-000000000000",
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_create_account_validates_payload(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "",
            "type": "",
            "currency_code": "US",
        },
    )

    assert response.status_code == 422


async def test_create_account_normalizes_currency_code(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "usd",
        },
    )

    assert response.status_code == 201
    assert response.json()["currency_code"] == "USD"


async def test_create_account_rejects_duplicate_name(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201

    duplicate_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Account name already exists."


async def test_create_account_rejects_invalid_type(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "not-a-type",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 422


async def test_update_account_rejects_unknown_currency(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/accounts/{account_id}", json={"currency_code": "ZZZ"}
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Unknown currency code."


async def test_update_account_requires_fields(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(f"/accounts/{account_id}", json={})

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "No fields to update."


async def test_update_account_validates_payload(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/accounts/{account_id}",
        json={"name": "", "type": "not-a-type", "currency_code": "US"},
    )

    assert update_response.status_code == 422


async def test_update_account_not_found(
    app, async_client, seeded_currencies
) -> None:
    update_response = await async_client.patch(
        "/accounts/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Account not found."


async def test_update_account_invalid_id(
    app, async_client, seeded_currencies
) -> None:
    update_response = await async_client.patch(
        "/accounts/not-a-uuid", json={"name": "Updated"}
    )

    assert update_response.status_code == 422


async def test_update_account_normalizes_currency_code(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/accounts/{account_id}", json={"currency_code": "eur"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["currency_code"] == "EUR"


async def test_update_account_rejects_duplicate_name(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Savings",
            "type": "savings",
            "currency_code": "USD",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    account_id = second_response.json()["id"]

    update_response = await async_client.patch(
        f"/accounts/{account_id}",
        json={"name": "Checking"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Account name already exists."


async def test_delete_account_not_found(
    app, async_client, seeded_currencies
) -> None:
    delete_response = await async_client.delete(
        "/accounts/00000000-0000-0000-0000-000000000000"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Account not found."


async def test_delete_account_invalid_id(
    app, async_client, seeded_currencies
) -> None:
    delete_response = await async_client.delete("/accounts/not-a-uuid")

    assert delete_response.status_code == 422


async def test_delete_account_has_empty_body(
    app, async_client, seeded_currencies
) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        "/accounts",
        json={
            "budget_id": budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    delete_response = await async_client.delete(f"/accounts/{account_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""


async def test_list_accounts_scoped_to_budget(
    app, async_client, seeded_currencies
) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": first_budget_id,
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        "/accounts",
        json={
            "budget_id": second_budget_id,
            "name": "Savings",
            "type": "savings",
            "currency_code": "USD",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{first_budget_id}/accounts")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["budget_id"] == first_budget_id
    assert payload[0]["name"] == "Checking"


async def test_list_accounts_rejects_unknown_budget(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.get(
        "/budgets/00000000-0000-0000-0000-000000000000/accounts"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_list_accounts_invalid_budget_id(
    app, async_client, seeded_currencies
) -> None:
    response = await async_client.get("/budgets/not-a-uuid/accounts")

    assert response.status_code == 422
