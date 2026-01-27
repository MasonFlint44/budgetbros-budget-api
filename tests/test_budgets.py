from uuid import UUID

from datetime import datetime, timezone

from sqlalchemy import select

from budget_api.tables import BudgetMembersTable, BudgetsTable, UsersTable
from budget_api.db import get_session_scope


async def test_create_budget(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Household"
    assert payload["base_currency_code"] == "USD"
    assert "id" in payload
    assert "created_at" in payload


async def test_budget_persists_in_db(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])

    async with get_session_scope() as session:
        budget = await session.get(BudgetsTable, budget_id)

        assert budget is not None
        assert budget.name == "Household"
        assert budget.base_currency_code == "USD"


async def test_list_budgets(app, async_client) -> None:
    before_response = await async_client.get("/budgets")
    assert before_response.status_code == 200
    before_ids = {budget["id"] for budget in before_response.json()}

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
    new_items = [item for item in payload if item["id"] not in before_ids]
    new_by_name = {item["name"]: item for item in new_items}
    assert "Household" in new_by_name
    assert "Vacation" in new_by_name
    assert new_by_name["Household"]["base_currency_code"] == "USD"
    assert new_by_name["Vacation"]["base_currency_code"] == "EUR"
    assert "id" in new_by_name["Household"]
    assert "created_at" in new_by_name["Household"]


async def test_update_budget(app, async_client) -> None:
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

    async with get_session_scope() as session:
        budget = await session.get(BudgetsTable, UUID(budget_id))

        assert budget is not None
        assert budget.name == "Updated"
        assert budget.base_currency_code == "EUR"


async def test_delete_budget(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = response.json()["id"]

    delete_response = await async_client.delete(f"/budgets/{budget_id}")

    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        budget = await session.get(BudgetsTable, UUID(budget_id))

        assert budget is None


async def test_list_budgets_empty(app, async_client) -> None:
    response = await async_client.get("/budgets")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


async def test_list_budgets_ordered_by_created_at(app, async_client) -> None:
    before_response = await async_client.get("/budgets")
    assert before_response.status_code == 200
    before_ids = {budget["id"] for budget in before_response.json()}

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
    new_items = [item for item in payload if item["id"] not in before_ids]
    new_names = [item["name"] for item in new_items]
    assert new_names == ["Alpha", "Beta"]


async def test_create_budget_rejects_unknown_currency(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "ZZZ"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown base currency code."


async def test_create_budget_validates_payload(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "", "base_currency_code": "US"}
    )

    assert response.status_code == 422


async def test_create_budget_normalizes_currency_code(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "usd"}
    )

    assert response.status_code == 201
    assert response.json()["base_currency_code"] == "USD"


async def test_update_budget_rejects_unknown_currency(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"base_currency_code": "ZZZ"}
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Unknown base currency code."


async def test_update_budget_requires_fields(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(f"/budgets/{budget_id}", json={})

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "No fields to update."


async def test_update_budget_validates_payload(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"name": "", "base_currency_code": "US"}
    )

    assert update_response.status_code == 422


async def test_update_budget_not_found(app, async_client) -> None:
    update_response = await async_client.patch(
        "/budgets/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Budget not found."


async def test_update_budget_invalid_id(app, async_client) -> None:
    update_response = await async_client.patch(
        "/budgets/not-a-uuid", json={"name": "Updated"}
    )

    assert update_response.status_code == 422


async def test_update_budget_normalizes_currency_code(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}", json={"base_currency_code": "eur"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["base_currency_code"] == "EUR"


async def test_delete_budget_not_found(app, async_client) -> None:
    delete_response = await async_client.delete(
        "/budgets/00000000-0000-0000-0000-000000000000"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Budget not found."


async def test_delete_budget_invalid_id(app, async_client) -> None:
    delete_response = await async_client.delete("/budgets/not-a-uuid")

    assert delete_response.status_code == 422


async def test_delete_budget_has_empty_body(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )
    budget_id = response.json()["id"]

    delete_response = await async_client.delete(f"/budgets/{budget_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""


async def test_list_budgets_scoped_to_member(app, async_client) -> None:
    await async_client.get("/budgets")

    response = await async_client.post(
        "/budgets", json={"name": "Mine", "base_currency_code": "USD"}
    )
    assert response.status_code == 201
    own_budget_id = response.json()["id"]

    now = datetime.now(timezone.utc)
    other_user_id = UUID("00000000-0000-0000-0000-000000000001")
    other_budget_id = UUID("00000000-0000-0000-0000-000000000002")

    async with get_session_scope() as session:
        session.add(
            UsersTable(
                id=other_user_id,
                email=f"other-{other_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=other_budget_id,
                name="Other",
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

    list_response = await async_client.get("/budgets")

    assert list_response.status_code == 200
    payload = list_response.json()
    assert any(item["id"] == own_budget_id for item in payload)
    assert all(item["id"] != str(other_budget_id) for item in payload)


async def test_update_budget_requires_membership(app, async_client) -> None:
    await async_client.get("/budgets")

    now = datetime.now(timezone.utc)
    other_user_id = UUID("00000000-0000-0000-0000-000000000003")
    other_budget_id = UUID("00000000-0000-0000-0000-000000000004")

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
        f"/budgets/{other_budget_id}",
        json={"name": "Updated"},
    )

    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Not authorized to update budget."


async def test_delete_budget_requires_owner(app, async_client) -> None:
    await async_client.get("/budgets")

    now = datetime.now(timezone.utc)
    owner_id = UUID("00000000-0000-0000-0000-000000000005")
    shared_budget_id = UUID("00000000-0000-0000-0000-000000000006")

    async with get_session_scope() as session:
        current_user = (
            await session.execute(
                select(UsersTable).where(UsersTable.email == "masonflint44@gmail.com")
            )
        ).scalar_one()
        session.add(
            UsersTable(
                id=owner_id,
                email=f"real-owner-{owner_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=shared_budget_id,
                name="Shared",
                owner_user_id=owner_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add_all(
            [
                BudgetMembersTable(
                    budget_id=shared_budget_id,
                    user_id=owner_id,
                ),
                BudgetMembersTable(
                    budget_id=shared_budget_id,
                    user_id=current_user.id,
                ),
            ]
        )
        await session.flush()

    delete_response = await async_client.delete(f"/budgets/{shared_budget_id}")

    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Not authorized to delete budget."

    async with get_session_scope() as session:
        budget = await session.get(BudgetsTable, shared_budget_id)
        assert budget is not None
