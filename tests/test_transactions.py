from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update

from budget_api.db import get_session_scope
from budget_api.tables import (
    CategoriesTable,
    PayeesTable,
    TransactionLinesTable,
    TransactionsTable,
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


async def create_category(budget_id: UUID) -> UUID:
    category_id = uuid4()
    async with get_session_scope() as session:
        session.add(
            CategoriesTable(
                id=category_id,
                budget_id=budget_id,
                name=f"Category-{category_id}",
                kind="expense",
                parent_id=None,
                is_archived=False,
                sort_order=0,
            )
        )
        await session.flush()
    return category_id


async def create_payee(budget_id: UUID) -> UUID:
    payee_id = uuid4()
    async with get_session_scope() as session:
        session.add(
            PayeesTable(
                id=payee_id,
                budget_id=budget_id,
                name=f"Payee-{payee_id}",
                is_archived=False,
            )
        )
        await session.flush()
    return payee_id


async def create_transaction(
    async_client, budget_id: str, account_id: str, *, posted_at: str | None = None
) -> dict:
    payload: dict[str, object] = {
        "line": {
            "account_id": account_id,
            "amount_minor": -500,
        }
    }
    if posted_at is not None:
        payload["posted_at"] = posted_at
    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


async def test_create_transaction(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    category_id = await create_category(UUID(budget_id))
    payee_id = await create_payee(UUID(budget_id))

    import_id = f"import-{uuid4()}"

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "posted_at": "2025-01-02T03:04:05",
            "status": "POSTED",
            "notes": "Dinner",
            "import_id": import_id,
            "line": {
                "account_id": account_id,
                "category_id": str(category_id),
                "payee_id": str(payee_id),
                "amount_minor": -1234,
                "memo": "Tacos",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["status"] == "posted"
    assert payload["notes"] == "Dinner"
    assert payload["import_id"] == import_id
    assert payload["posted_at"].startswith("2025-01-02T03:04:05")
    assert payload["posted_at"].endswith(("Z", "+00:00"))

    assert payload["lines"]
    assert len(payload["lines"]) == 1
    line = payload["lines"][0]
    assert line["account_id"] == account_id
    assert line["category_id"] == str(category_id)
    assert line["payee_id"] == str(payee_id)
    assert line["amount_minor"] == -1234
    assert line["memo"] == "Tacos"
    assert line["tag_ids"] == []

    transaction_id = UUID(payload["id"])
    async with get_session_scope() as session:
        transaction = await session.get(TransactionsTable, transaction_id)
        assert transaction is not None
        assert transaction.budget_id == UUID(budget_id)
        assert transaction.status == "posted"

        result = await session.execute(
            select(TransactionLinesTable).where(
                TransactionLinesTable.transaction_id == transaction_id
            )
        )
        lines = result.scalars().all()
        assert len(lines) == 1
        line_row = lines[0]
        assert line_row.account_id == UUID(account_id)
        assert line_row.category_id == category_id
        assert line_row.payee_id == payee_id
        assert line_row.amount_minor == -1234
        assert line_row.memo == "Tacos"


async def test_create_transaction_rejects_unknown_account(app, async_client) -> None:
    budget_id = await create_budget(async_client)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": str(uuid4()),
                "amount_minor": -500,
            }
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Account not found."


async def test_create_transaction_rejects_unknown_category(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "category_id": str(uuid4()),
                "amount_minor": -500,
            }
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found."


async def test_create_transaction_rejects_unknown_payee(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "payee_id": str(uuid4()),
                "amount_minor": -500,
            }
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Payee not found."


async def test_create_transaction_rejects_zero_amount(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "amount_minor": 0,
            }
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Amount must be non-zero."


async def test_list_transactions_respects_budget_scoping(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    other_budget_id = await create_budget(async_client)
    other_account_id = await create_account(async_client, other_budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    await create_transaction(async_client, other_budget_id, other_account_id)

    response = await async_client.get(f"/budgets/{budget_id}/transactions")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == transaction["id"]
    assert payload[0]["budget_id"] == budget_id
    assert payload[0]["lines"]


async def test_list_transactions_ordered_by_posted_at_created_at_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction_newest = await create_transaction(
        async_client, budget_id, account_id, posted_at="2025-01-04T10:00:00"
    )
    transaction_a = await create_transaction(
        async_client, budget_id, account_id, posted_at="2025-01-03T10:00:00"
    )
    transaction_b = await create_transaction(
        async_client, budget_id, account_id, posted_at="2025-01-03T10:00:00"
    )
    transaction_c = await create_transaction(
        async_client, budget_id, account_id, posted_at="2025-01-03T10:00:00"
    )

    transaction_a_id = UUID(transaction_a["id"])
    transaction_b_id = UUID(transaction_b["id"])
    transaction_c_id = UUID(transaction_c["id"])

    async with get_session_scope() as session:
        await session.execute(
            update(TransactionsTable)
            .where(TransactionsTable.id == transaction_a_id)
            .values(created_at=datetime(2025, 1, 2, tzinfo=timezone.utc))
        )
        await session.execute(
            update(TransactionsTable)
            .where(TransactionsTable.id == transaction_b_id)
            .values(created_at=datetime(2025, 1, 1, 12, tzinfo=timezone.utc))
        )
        await session.execute(
            update(TransactionsTable)
            .where(TransactionsTable.id == transaction_c_id)
            .values(created_at=datetime(2025, 1, 1, 12, tzinfo=timezone.utc))
        )

    response = await async_client.get(f"/budgets/{budget_id}/transactions")

    assert response.status_code == 200
    payload = response.json()

    if transaction_b_id.int > transaction_c_id.int:
        tail_ids = [transaction_b["id"], transaction_c["id"]]
    else:
        tail_ids = [transaction_c["id"], transaction_b["id"]]

    assert [item["id"] for item in payload] == [
        transaction_newest["id"],
        transaction_a["id"],
        *tail_ids,
    ]


async def test_list_transactions_excludes_lines_when_requested(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)

    response = await async_client.get(
        f"/budgets/{budget_id}/transactions?include_lines=false"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == transaction["id"]
    assert payload[0]["lines"] is None
