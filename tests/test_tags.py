from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from budget_api.db import get_session_scope
from budget_api.tables import (
    BudgetMembersTable,
    BudgetsTable,
    TagsTable,
    TransactionLineTagsTable,
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


async def test_create_tag(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Travel"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Travel"
    assert "id" in payload


async def test_tag_persists_in_db(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Utilities"},
    )
    assert response.status_code == 201
    tag_id = UUID(response.json()["id"])

    async with get_session_scope() as session:
        tag = await session.get(TagsTable, tag_id)
        assert tag is not None
        assert tag.budget_id == UUID(budget_id)
        assert tag.name == "Utilities"


async def test_list_tags_orders_by_name_then_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response_a = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Zulu"},
    )
    response_b = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Beta"},
    )
    response_c = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Alpha"},
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_c.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/tags")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta", "Zulu"]
    assert [
        (item["name"], item["id"])
        for item in payload
    ] == sorted((item["name"], item["id"]) for item in payload)


async def test_get_tag(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Groceries"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.get(f"/budgets/{budget_id}/tags/{tag_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == tag_id
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Groceries"


async def test_update_tag(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Old Name"},
    )
    tag_id = create_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/tags/{tag_id}",
        json={"name": "New Name"},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == tag_id
    assert payload["name"] == "New Name"


async def test_delete_tag(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "To Delete"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.delete(f"/budgets/{budget_id}/tags/{tag_id}")

    assert response.status_code == 204
    assert response.content == b""

    async with get_session_scope() as session:
        tag = await session.get(TagsTable, UUID(tag_id))
        assert tag is None


async def test_create_tag_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Rent"},
    )
    assert first_response.status_code == 201

    duplicate_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Rent"},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Tag name already exists."


async def test_update_tag_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Fixed"},
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Variable"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    second_id = second_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/tags/{second_id}",
        json={"name": "Fixed"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Tag name already exists."


async def test_update_tag_requires_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Needs Update"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/tags/{tag_id}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update."


async def test_update_tag_rejects_null_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Needs Update"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/tags/{tag_id}",
        json={"name": None},
    )

    assert response.status_code == 422


async def test_get_tag_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/tags",
        json={"name": "Scoped"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.get(f"/budgets/{second_budget_id}/tags/{tag_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found."


async def test_update_tag_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/tags",
        json={"name": "Scoped"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{second_budget_id}/tags/{tag_id}",
        json={"name": "Updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found."


async def test_delete_tag_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/tags",
        json={"name": "Scoped"},
    )
    tag_id = create_response.json()["id"]

    response = await async_client.delete(f"/budgets/{second_budget_id}/tags/{tag_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found."


async def test_list_tags_is_budget_scoped(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{first_budget_id}/tags",
        json={"name": "First"},
    )
    second_response = await async_client.post(
        f"/budgets/{second_budget_id}/tags",
        json={"name": "Second"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{first_budget_id}/tags")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["budget_id"] == first_budget_id
    assert payload[0]["name"] == "First"


async def test_list_tags_rejects_unknown_budget(app, async_client) -> None:
    response = await async_client.get("/budgets/00000000-0000-0000-0000-000000000000/tags")

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_tags_require_membership(app, async_client) -> None:
    private_budget_id = await create_private_budget()

    list_response = await async_client.get(f"/budgets/{private_budget_id}/tags")
    create_response = await async_client.post(
        f"/budgets/{private_budget_id}/tags",
        json={"name": "Private"},
    )
    get_response = await async_client.get(
        f"/budgets/{private_budget_id}/tags/{uuid4()}"
    )
    update_response = await async_client.patch(
        f"/budgets/{private_budget_id}/tags/{uuid4()}",
        json={"name": "Updated"},
    )
    delete_response = await async_client.delete(
        f"/budgets/{private_budget_id}/tags/{uuid4()}"
    )

    assert list_response.status_code == 403
    assert list_response.json()["detail"] == "Not authorized to view tags."
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == "Not authorized to manage tags."
    assert get_response.status_code == 403
    assert get_response.json()["detail"] == "Not authorized to view tags."
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Not authorized to manage tags."
    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Not authorized to manage tags."


async def test_delete_tag_removes_transaction_line_associations(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    tag_response = await async_client.post(
        f"/budgets/{budget_id}/tags",
        json={"name": "Food"},
    )
    assert tag_response.status_code == 201
    tag_id = tag_response.json()["id"]

    create_transaction_response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "amount_minor": -2500,
                "tag_ids": [tag_id],
            }
        },
    )
    assert create_transaction_response.status_code == 201
    transaction_payload = create_transaction_response.json()
    transaction_id = transaction_payload["id"]
    line = transaction_payload["lines"][0]
    line_id = line["id"]
    assert line["tag_ids"] == [tag_id]

    async with get_session_scope() as session:
        links_result = await session.execute(
            select(TransactionLineTagsTable).where(
                TransactionLineTagsTable.line_id == UUID(line_id)
            )
        )
        links = links_result.scalars().all()
        assert len(links) == 1
        assert links[0].tag_id == UUID(tag_id)

    delete_response = await async_client.delete(f"/budgets/{budget_id}/tags/{tag_id}")
    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        tag = await session.get(TagsTable, UUID(tag_id))
        assert tag is None

        links_result = await session.execute(
            select(TransactionLineTagsTable).where(
                TransactionLineTagsTable.line_id == UUID(line_id)
            )
        )
        assert links_result.scalars().all() == []

    get_transaction_response = await async_client.get(
        f"/budgets/{budget_id}/transactions/{transaction_id}"
    )
    assert get_transaction_response.status_code == 200
    updated_line = get_transaction_response.json()["lines"][0]
    assert updated_line["tag_ids"] == []
