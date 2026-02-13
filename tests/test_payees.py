from datetime import datetime, timezone
from uuid import UUID, uuid4

from budget_api.db import get_session_scope
from budget_api.tables import (
    BudgetMembersTable,
    BudgetsTable,
    PayeesTable,
    TransactionLinesTable,
    UsersTable,
)


async def create_budget(async_client, *, base_currency_code: str = "USD") -> str:
    response = await async_client.post(
        "/budgets",
        json={
            "name": f"Budget-{uuid4()}",
            "base_currency_code": base_currency_code,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_account(async_client, budget_id: str) -> str:
    response = await async_client.post(
        f"/budgets/{budget_id}/accounts",
        json={
            "name": f"Checking-{uuid4()}",
            "type": "checking",
            "currency_code": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_private_budget() -> UUID:
    owner_id = uuid4()
    budget_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=owner_id,
                email=f"owner-{owner_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=budget_id,
                name=f"Private-{budget_id}",
                owner_user_id=owner_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=budget_id,
                user_id=owner_id,
            )
        )
        await session.flush()

    return budget_id


async def test_create_payee(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Trader Joe's"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Trader Joe's"
    assert "id" in payload


async def test_payee_persists_in_db(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Utilities"},
    )
    assert response.status_code == 201
    payee_id = UUID(response.json()["id"])

    async with get_session_scope() as session:
        payee = await session.get(PayeesTable, payee_id)
        assert payee is not None
        assert payee.budget_id == UUID(budget_id)
        assert payee.name == "Utilities"


async def test_list_payees_orders_by_name_then_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response_a = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Zulu"},
    )
    response_b = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Beta"},
    )
    response_c = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Alpha"},
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_c.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/payees")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta", "Zulu"]


async def test_get_payee(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Coffee Shop"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.get(f"/budgets/{budget_id}/payees/{payee_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == payee_id
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Coffee Shop"


async def test_update_payee(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Old Name"},
    )
    payee_id = create_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/payees/{payee_id}",
        json={"name": "New Name"},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == payee_id
    assert payload["name"] == "New Name"


async def test_delete_payee(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "To Delete"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.delete(f"/budgets/{budget_id}/payees/{payee_id}")

    assert response.status_code == 204
    assert response.content == b""

    async with get_session_scope() as session:
        payee = await session.get(PayeesTable, UUID(payee_id))
        assert payee is None


async def test_delete_payee_sets_transaction_line_payee_to_null(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    create_payee_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Restaurant"},
    )
    payee_id = create_payee_response.json()["id"]

    create_transaction_response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "payee_id": payee_id,
                "amount_minor": -2200,
            }
        },
    )
    assert create_transaction_response.status_code == 201
    line_id = create_transaction_response.json()["lines"][0]["id"]

    delete_response = await async_client.delete(f"/budgets/{budget_id}/payees/{payee_id}")
    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        line = await session.get(TransactionLinesTable, UUID(line_id))
        assert line is not None
        assert line.payee_id is None


async def test_create_payee_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Landlord"},
    )
    assert first_response.status_code == 201

    duplicate_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Landlord"},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Payee name already exists."


async def test_update_payee_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Fixed"},
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Variable"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    second_id = second_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/payees/{second_id}",
        json={"name": "Fixed"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Payee name already exists."


async def test_update_payee_requires_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Needs Update"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/payees/{payee_id}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update."


async def test_update_payee_rejects_null_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Needs Update"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/payees/{payee_id}",
        json={"name": None},
    )

    assert response.status_code == 422


async def test_get_payee_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/payees",
        json={"name": "Scoped"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.get(f"/budgets/{second_budget_id}/payees/{payee_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_update_payee_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/payees",
        json={"name": "Scoped"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{second_budget_id}/payees/{payee_id}",
        json={"name": "Updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_delete_payee_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/payees",
        json={"name": "Scoped"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.delete(f"/budgets/{second_budget_id}/payees/{payee_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_list_payees_rejects_unknown_budget(app, async_client) -> None:
    response = await async_client.get("/budgets/00000000-0000-0000-0000-000000000000/payees")

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_payees_require_membership(app, async_client) -> None:
    private_budget_id = await create_private_budget()

    list_response = await async_client.get(f"/budgets/{private_budget_id}/payees")
    create_response = await async_client.post(
        f"/budgets/{private_budget_id}/payees",
        json={"name": "Private"},
    )
    get_response = await async_client.get(
        f"/budgets/{private_budget_id}/payees/{uuid4()}"
    )
    update_response = await async_client.patch(
        f"/budgets/{private_budget_id}/payees/{uuid4()}",
        json={"name": "Updated"},
    )
    delete_response = await async_client.delete(
        f"/budgets/{private_budget_id}/payees/{uuid4()}"
    )

    assert list_response.status_code == 403
    assert list_response.json()["detail"] == "Not authorized to view payees."
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == "Not authorized to manage payees."
    assert get_response.status_code == 403
    assert get_response.json()["detail"] == "Not authorized to view payees."
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Not authorized to manage payees."
    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Not authorized to manage payees."


async def test_get_payee_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.get(
        f"/budgets/{budget_id}/payees/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_update_payee_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.patch(
        f"/budgets/{budget_id}/payees/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_delete_payee_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.delete(
        f"/budgets/{budget_id}/payees/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payee not found."


async def test_payee_create_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": ""},
    )

    assert response.status_code == 422


async def test_payee_update_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/payees",
        json={"name": "Vendor"},
    )
    payee_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/payees/{payee_id}",
        json={"name": ""},
    )

    assert response.status_code == 422


async def test_list_payees_is_budget_scoped(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{first_budget_id}/payees",
        json={"name": "First"},
    )
    second_response = await async_client.post(
        f"/budgets/{second_budget_id}/payees",
        json={"name": "Second"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{first_budget_id}/payees")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["budget_id"] == first_budget_id
    assert payload[0]["name"] == "First"
