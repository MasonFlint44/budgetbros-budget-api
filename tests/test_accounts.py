from datetime import datetime, timezone
from uuid import UUID, uuid4

from budget_api.db import get_session_scope
from budget_api.tables import (
    AccountsTable,
    BudgetMembersTable,
    BudgetsTable,
    UsersTable,
)


async def create_budget(async_client, *, base_currency_code: str = "USD") -> str:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": base_currency_code}
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_account(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
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
    assert payload["is_active"] is True
    assert "id" in payload
    assert "created_at" in payload


async def test_account_persists_in_db(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = UUID(response.json()["id"])

    async with get_session_scope() as session:
        account = await session.get(AccountsTable, account_id)

        assert account is not None
        assert account.name == "Checking"
        assert account.type == "checking"
        assert account.currency_code == "USD"
        assert account.is_active is True


async def test_list_accounts(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Savings",
            "type": "savings",
            "currency_code": "USD",
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
    assert payload[1]["currency_code"] == "USD"
    assert "id" in payload[0]
    assert "created_at" in payload[0]


async def test_update_account(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}",
        json={
            "name": "Updated",
            "type": "savings",
            "currency_code": "USD",
            "is_active": False,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == account_id
    assert payload["name"] == "Updated"
    assert payload["type"] == "savings"
    assert payload["currency_code"] == "USD"
    assert payload["is_active"] is False

    async with get_session_scope() as session:
        account = await session.get(AccountsTable, UUID(account_id))

        assert account is not None
        assert account.name == "Updated"
        assert account.type == "savings"
        assert account.currency_code == "USD"
        assert account.is_active is False


async def test_delete_account(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201
    account_id = response.json()["id"]

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/accounts/{account_id}"
    )

    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        account = await session.get(AccountsTable, UUID(account_id))

        assert account is None


async def test_list_accounts_empty(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.get(f"/budgets/{budget_id}/accounts")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_accounts_ordered_by_created_at(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Alpha",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Beta",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/accounts")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta"]


async def test_create_account_rejects_unknown_currency(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "ZZZ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown currency code."


async def test_create_account_rejects_currency_mismatch(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "EUR",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Account currency must match budget base currency."
    )


async def test_create_account_rejects_unknown_budget(app, async_client) -> None:
    response = await async_client.post(
        "/budgets/00000000-0000-0000-0000-000000000000/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_create_account_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "",
            "type": "",
            "currency_code": "US",
        },
    )

    assert response.status_code == 422


async def test_create_account_normalizes_currency_code(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "usd",
        },
    )

    assert response.status_code == 201
    assert response.json()["currency_code"] == "USD"


async def test_create_account_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 201

    duplicate_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Account name already exists."


async def test_create_account_rejects_invalid_type(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "not-a-type",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 422


async def test_update_account_rejects_unknown_currency(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}", json={"currency_code": "ZZZ"}
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Unknown currency code."


async def test_update_account_rejects_currency_mismatch(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}",
        json={"currency_code": "EUR"},
    )

    assert update_response.status_code == 400
    assert (
        update_response.json()["detail"]
        == "Account currency must match budget base currency."
    )


async def test_update_account_requires_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}", json={}
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "No fields to update."


async def test_update_account_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}",
        json={"name": "", "type": "not-a-type", "currency_code": "US"},
    )

    assert update_response.status_code == 422


async def test_update_account_rejects_null_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}",
        json={"name": None},
    )

    assert update_response.status_code == 422


async def test_update_account_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Account not found."


async def test_update_account_invalid_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/not-a-uuid", json={"name": "Updated"}
    )

    assert update_response.status_code == 422


async def test_update_account_normalizes_currency_code(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}", json={"currency_code": "usd"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["currency_code"] == "USD"


async def test_update_account_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Savings",
            "type": "savings",
            "currency_code": "USD",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    account_id = second_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/accounts/{account_id}",
        json={"name": "Checking"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Account name already exists."


async def test_delete_account_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/accounts/00000000-0000-0000-0000-000000000000"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Account not found."


async def test_delete_account_invalid_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/accounts/not-a-uuid"
    )

    assert delete_response.status_code == 422


async def test_delete_account_has_empty_body(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/accounts/{account_id}"
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""


async def test_list_accounts_scoped_to_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{first_budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    second_response = await async_client.post(
        f"/budgets/{second_budget_id}/accounts",
        json={
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


async def test_list_accounts_rejects_unknown_budget(app, async_client) -> None:
    response = await async_client.get(
        "/budgets/00000000-0000-0000-0000-000000000000/accounts"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_list_accounts_invalid_budget_id(app, async_client) -> None:
    response = await async_client.get("/budgets/not-a-uuid/accounts")

    assert response.status_code == 422


async def test_account_list_requires_membership(app, async_client) -> None:
    await async_client.get("/budgets")

    other_user_id = uuid4()
    other_budget_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=other_user_id,
                email=f"owner-{other_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=other_budget_id,
                name="Private",
                owner_user_id=other_user_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=other_budget_id,
                user_id=other_user_id,
            )
        )
        await session.flush()

    response = await async_client.get(f"/budgets/{other_budget_id}/accounts")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view accounts."


async def test_account_create_requires_membership(app, async_client) -> None:
    await async_client.get("/budgets")

    other_user_id = uuid4()
    other_budget_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=other_user_id,
                email=f"owner-{other_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=other_budget_id,
                name="Private",
                owner_user_id=other_user_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=other_budget_id,
                user_id=other_user_id,
            )
        )
        await session.flush()

    response = await async_client.post(
        f"/budgets/{other_budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to manage accounts."


async def test_account_update_requires_membership(app, async_client) -> None:
    await async_client.get("/budgets")

    other_user_id = uuid4()
    other_budget_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=other_user_id,
                email=f"owner-{other_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=other_budget_id,
                name="Private",
                owner_user_id=other_user_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=other_budget_id,
                user_id=other_user_id,
            )
        )
        await session.flush()

    update_response = await async_client.patch(
        f"/budgets/{other_budget_id}/accounts/{uuid4()}",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Not authorized to manage accounts."


async def test_account_delete_requires_membership(app, async_client) -> None:
    await async_client.get("/budgets")

    other_user_id = uuid4()
    other_budget_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=other_user_id,
                email=f"owner-{other_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=other_budget_id,
                name="Private",
                owner_user_id=other_user_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=other_budget_id,
                user_id=other_user_id,
            )
        )
        await session.flush()

    delete_response = await async_client.delete(
        f"/budgets/{other_budget_id}/accounts/{uuid4()}"
    )

    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Not authorized to manage accounts."


async def test_update_account_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{first_budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{second_budget_id}/accounts/{account_id}",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Account not found."


async def test_delete_account_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{first_budget_id}/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    account_id = response.json()["id"]

    delete_response = await async_client.delete(
        f"/budgets/{second_budget_id}/accounts/{account_id}"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Account not found."
