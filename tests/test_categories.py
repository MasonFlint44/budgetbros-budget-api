from datetime import datetime, timezone
from uuid import UUID, uuid4

from budget_api.db import get_session_scope
from budget_api.tables import (
    BudgetMembersTable,
    BudgetsTable,
    CategoriesTable,
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


async def test_create_category(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Groceries"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Groceries"
    assert payload["parent_id"] is None
    assert payload["is_archived"] is False
    assert payload["sort_order"] == 0


async def test_category_persists_in_db(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Utilities", "is_archived": True, "sort_order": 9},
    )
    assert response.status_code == 201
    category_id = UUID(response.json()["id"])

    async with get_session_scope() as session:
        category = await session.get(CategoriesTable, category_id)
        assert category is not None
        assert category.budget_id == UUID(budget_id)
        assert category.name == "Utilities"
        assert category.parent_id is None
        assert category.is_archived is True
        assert category.sort_order == 9


async def test_list_categories_orders_by_sort_order_then_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response_a = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Zulu", "sort_order": 2},
    )
    response_b = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Beta", "sort_order": 1},
    )
    response_c = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Alpha", "sort_order": 1},
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_c.status_code == 201

    response = await async_client.get(f"/budgets/{budget_id}/categories")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Alpha", "Beta", "Zulu"]


async def test_get_category(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Insurance"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.get(f"/budgets/{budget_id}/categories/{category_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == category_id
    assert payload["budget_id"] == budget_id
    assert payload["name"] == "Insurance"


async def test_update_category(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Subscriptions"},
    )
    category_id = create_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{category_id}",
        json={"name": "Recurring", "is_archived": True, "sort_order": 5},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["id"] == category_id
    assert payload["name"] == "Recurring"
    assert payload["is_archived"] is True
    assert payload["sort_order"] == 5


async def test_delete_category(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "To Delete"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.delete(f"/budgets/{budget_id}/categories/{category_id}")

    assert response.status_code == 204
    assert response.content == b""

    async with get_session_scope() as session:
        category = await session.get(CategoriesTable, UUID(category_id))
        assert category is None


async def test_delete_category_sets_transaction_line_category_to_null(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    create_category_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Dining"},
    )
    category_id = create_category_response.json()["id"]

    create_transaction_response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "category_id": category_id,
                "amount_minor": -1500,
            }
        },
    )
    assert create_transaction_response.status_code == 201
    line_id = create_transaction_response.json()["lines"][0]["id"]

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/categories/{category_id}"
    )
    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        line = await session.get(TransactionLinesTable, UUID(line_id))
        assert line is not None
        assert line.category_id is None


async def test_create_category_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Rent"},
    )
    assert first_response.status_code == 201

    duplicate_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Rent"},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Category name already exists."


async def test_update_category_rejects_duplicate_name(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Fixed"},
    )
    second_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Variable"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    second_id = second_response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{second_id}",
        json={"name": "Fixed"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Category name already exists."


async def test_create_category_rejects_unknown_parent(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Child", "parent_id": str(uuid4())},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Parent category not found."


async def test_create_category_rejects_cross_budget_parent(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    parent_response = await async_client.post(
        f"/budgets/{first_budget_id}/categories",
        json={"name": "Parent"},
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    response = await async_client.post(
        f"/budgets/{second_budget_id}/categories",
        json={"name": "Child", "parent_id": parent_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Parent category not found."


async def test_create_category_rejects_grandchild(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    parent_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Parent"},
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Child", "parent_id": parent_id},
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    grandchild_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Grandchild", "parent_id": child_id},
    )

    assert grandchild_response.status_code == 400
    assert (
        grandchild_response.json()["detail"]
        == "Nested categories cannot be deeper than one level."
    )


async def test_update_category_rejects_self_parent(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Self"},
    )
    assert create_response.status_code == 201
    category_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{category_id}",
        json={"parent_id": category_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category cannot be its own parent."


async def test_update_category_rejects_parent_that_is_already_nested(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    parent_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Top Parent"},
    )
    assert parent_response.status_code == 201
    top_parent_id = parent_response.json()["id"]

    child_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Child", "parent_id": top_parent_id},
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    update_target_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Target"},
    )
    assert update_target_response.status_code == 201
    target_id = update_target_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{target_id}",
        json={"parent_id": child_id},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Nested categories cannot be deeper than one level."
    )


async def test_update_category_rejects_assigning_parent_when_category_has_children(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)

    parent_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Parent"},
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Child", "parent_id": parent_id},
    )
    assert child_response.status_code == 201

    new_parent_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Other Parent"},
    )
    assert new_parent_response.status_code == 201
    new_parent_id = new_parent_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{parent_id}",
        json={"parent_id": new_parent_id},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Nested categories cannot be deeper than one level."
    )


async def test_update_category_requires_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Needs Update"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{category_id}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update."


async def test_update_category_rejects_null_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Needs Update"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{category_id}",
        json={"name": None},
    )

    assert response.status_code == 422


async def test_get_category_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/categories",
        json={"name": "Scoped"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.get(
        f"/budgets/{second_budget_id}/categories/{category_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_update_category_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/categories",
        json={"name": "Scoped"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{second_budget_id}/categories/{category_id}",
        json={"name": "Updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_delete_category_rejects_mismatched_budget(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    create_response = await async_client.post(
        f"/budgets/{first_budget_id}/categories",
        json={"name": "Scoped"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.delete(
        f"/budgets/{second_budget_id}/categories/{category_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_list_categories_rejects_unknown_budget(app, async_client) -> None:
    response = await async_client.get(
        "/budgets/00000000-0000-0000-0000-000000000000/categories"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Budget not found."


async def test_categories_require_membership(app, async_client) -> None:
    private_budget_id = await create_private_budget()

    list_response = await async_client.get(f"/budgets/{private_budget_id}/categories")
    create_response = await async_client.post(
        f"/budgets/{private_budget_id}/categories",
        json={"name": "Private"},
    )
    get_response = await async_client.get(
        f"/budgets/{private_budget_id}/categories/{uuid4()}"
    )
    update_response = await async_client.patch(
        f"/budgets/{private_budget_id}/categories/{uuid4()}",
        json={"name": "Updated"},
    )
    delete_response = await async_client.delete(
        f"/budgets/{private_budget_id}/categories/{uuid4()}"
    )

    assert list_response.status_code == 403
    assert list_response.json()["detail"] == "Not authorized to view categories."
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == "Not authorized to manage categories."
    assert get_response.status_code == 403
    assert get_response.json()["detail"] == "Not authorized to view categories."
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Not authorized to manage categories."
    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Not authorized to manage categories."


async def test_get_category_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.get(
        f"/budgets/{budget_id}/categories/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_update_category_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_delete_category_not_found(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.delete(
        f"/budgets/{budget_id}/categories/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found."


async def test_category_create_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": ""},
    )

    assert response.status_code == 422


async def test_category_update_validates_payload(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    create_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Food"},
    )
    category_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/categories/{category_id}",
        json={"name": ""},
    )

    assert response.status_code == 422


async def test_delete_parent_category_nulls_child_parent_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    parent_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Parent"},
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_response = await async_client.post(
        f"/budgets/{budget_id}/categories",
        json={"name": "Child", "parent_id": parent_id},
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/categories/{parent_id}"
    )
    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        child = await session.get(CategoriesTable, UUID(child_id))
        assert child is not None
        assert child.parent_id is None


async def test_list_categories_is_budget_scoped(app, async_client) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)

    first_response = await async_client.post(
        f"/budgets/{first_budget_id}/categories",
        json={"name": "First"},
    )
    second_response = await async_client.post(
        f"/budgets/{second_budget_id}/categories",
        json={"name": "Second"},
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = await async_client.get(f"/budgets/{first_budget_id}/categories")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["budget_id"] == first_budget_id
    assert payload[0]["name"] == "First"
