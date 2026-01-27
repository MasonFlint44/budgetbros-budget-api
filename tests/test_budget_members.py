from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from budget_api.tables import BudgetMembersTable, BudgetsTable, UsersTable
from budget_api.db import get_db_session


async def test_create_budget_creates_membership(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Household", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])

    async with get_db_session() as session:
        result = await session.execute(select(UsersTable))
        user = result.scalar_one_or_none()
        assert user is not None

        result = await session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
                BudgetMembersTable.user_id == user.id,
            )
        )
        assert result.scalar_one_or_none() is not None


async def test_add_and_remove_budget_member(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Shared", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])
    new_user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_db_session() as session:
        session.add(
            UsersTable(
                id=new_user_id,
                email=f"member-{new_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()

    add_response = await async_client.post(
        f"/budgets/{budget_id}/members",
        json={"user_id": str(new_user_id)},
    )

    assert add_response.status_code == 204

    async with get_db_session() as session:
        result = await session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
                BudgetMembersTable.user_id == new_user_id,
            )
        )
        assert result.scalar_one_or_none() is not None

    remove_response = await async_client.delete(
        f"/budgets/{budget_id}/members/{new_user_id}"
    )

    assert remove_response.status_code == 204

    async with get_db_session() as session:
        result = await session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
                BudgetMembersTable.user_id == new_user_id,
            )
        )
        assert result.scalar_one_or_none() is None


async def test_delete_budget_removes_memberships(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Delete Me", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])
    extra_user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_db_session() as session:
        session.add(
            UsersTable(
                id=extra_user_id,
                email=f"extra-member-{extra_user_id}@example.com",
                created_at=now,
                last_seen_at=now,
            )
        )
        await session.flush()

    add_response = await async_client.post(
        f"/budgets/{budget_id}/members",
        json={"user_id": str(extra_user_id)},
    )

    assert add_response.status_code == 204

    async with get_db_session() as session:
        result = await session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
            )
        )
        assert result.scalars().all()

    delete_response = await async_client.delete(f"/budgets/{budget_id}")

    assert delete_response.status_code == 204

    async with get_db_session() as session:
        result = await session.execute(
            select(BudgetMembersTable).where(
                BudgetMembersTable.budget_id == budget_id,
            )
        )
        assert result.scalars().all() == []


async def test_list_budget_members(app, async_client) -> None:
    response = await async_client.post(
        "/budgets", json={"name": "Team", "base_currency_code": "USD"}
    )

    assert response.status_code == 201
    budget_id = UUID(response.json()["id"])
    extra_user_id = uuid4()
    now = datetime.now(timezone.utc)
    extra_email = f"team-member-{extra_user_id}@example.com"

    async with get_db_session() as session:
        session.add(
            UsersTable(
                id=extra_user_id,
                email=extra_email,
                created_at=now,
                last_seen_at=now,
            )
        )
        session.add(
            BudgetMembersTable(
                budget_id=budget_id,
                user_id=extra_user_id,
            )
        )
        await session.flush()

    list_response = await async_client.get(f"/budgets/{budget_id}/members")

    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 2
    assert {member["email"] for member in payload} == {
        "masonflint44@gmail.com",
        extra_email,
    }


async def test_list_budget_members_rejects_non_member(app, async_client) -> None:
    budget_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(timezone.utc)

    async with get_db_session() as session:
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
                name="Private",
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

    response = await async_client.get(f"/budgets/{budget_id}/members")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view budget members."


async def test_add_budget_member_requires_owner(app, async_client) -> None:
    now = datetime.now(timezone.utc)
    owner_id = uuid4()
    budget_id = uuid4()
    new_member_id = uuid4()

    async with get_db_session() as session:
        session.add_all(
            [
                UsersTable(
                    id=owner_id,
                    email=f"owner-{owner_id}@example.com",
                    created_at=now,
                    last_seen_at=now,
                ),
                UsersTable(
                    id=new_member_id,
                    email=f"new-member-{new_member_id}@example.com",
                    created_at=now,
                    last_seen_at=now,
                ),
            ]
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=budget_id,
                name="Owner Only",
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

    response = await async_client.post(
        f"/budgets/{budget_id}/members",
        json={"user_id": str(new_member_id)},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to manage budget members."


async def test_remove_budget_member_requires_owner(app, async_client) -> None:
    now = datetime.now(timezone.utc)
    owner_id = uuid4()
    budget_id = uuid4()
    existing_member_id = uuid4()

    async with get_db_session() as session:
        session.add_all(
            [
                UsersTable(
                    id=owner_id,
                    email=f"owner2-{owner_id}@example.com",
                    created_at=now,
                    last_seen_at=now,
                ),
                UsersTable(
                    id=existing_member_id,
                    email=f"member2-{existing_member_id}@example.com",
                    created_at=now,
                    last_seen_at=now,
                ),
            ]
        )
        await session.flush()
        session.add(
            BudgetsTable(
                id=budget_id,
                name="Owner Only 2",
                owner_user_id=owner_id,
                base_currency_code="USD",
                created_at=now,
            )
        )
        session.add_all(
            [
                BudgetMembersTable(
                    budget_id=budget_id,
                    user_id=owner_id,
                ),
                BudgetMembersTable(
                    budget_id=budget_id,
                    user_id=existing_member_id,
                ),
            ]
        )
        await session.flush()

    response = await async_client.delete(
        f"/budgets/{budget_id}/members/{existing_member_id}"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to manage budget members."
