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


async def add_transaction_line(
    transaction_id: UUID,
    account_id: UUID,
    *,
    category_id: UUID | None = None,
    payee_id: UUID | None = None,
    amount_minor: int = -500,
    memo: str | None = None,
) -> UUID:
    line_id = uuid4()
    async with get_session_scope() as session:
        session.add(
            TransactionLinesTable(
                id=line_id,
                transaction_id=transaction_id,
                account_id=account_id,
                category_id=category_id,
                payee_id=payee_id,
                amount_minor=amount_minor,
                memo=memo,
            )
        )
        await session.flush()
    return line_id


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


async def test_get_transaction_returns_200(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)

    response = await async_client.get(
        f"/budgets/{budget_id}/transactions/{transaction['id']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == transaction["id"]
    assert payload["budget_id"] == budget_id
    assert payload["lines"]
    assert payload["lines"][0]["account_id"] == account_id


async def test_get_transaction_excludes_lines_when_requested(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)

    response = await async_client.get(
        f"/budgets/{budget_id}/transactions/{transaction['id']}?include_lines=false"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == transaction["id"]
    assert payload["lines"] is None


async def test_get_transaction_from_another_budget_returns_404(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    transaction = await create_transaction(async_client, budget_id, account_id)

    other_budget_id = await create_budget(async_client)

    response = await async_client.get(
        f"/budgets/{other_budget_id}/transactions/{transaction['id']}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found."


async def test_update_transaction_fields(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = transaction["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction_id}",
        json={
            "posted_at": "2025-02-03T04:05:06",
            "status": "RECONCILED",
            "notes": "Updated",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == transaction_id
    assert payload["status"] == "reconciled"
    assert payload["notes"] == "Updated"
    assert payload["posted_at"].startswith("2025-02-03T04:05:06")
    assert payload["posted_at"].endswith(("Z", "+00:00"))
    assert payload["lines"]

    async with get_session_scope() as session:
        transaction_row = await session.get(TransactionsTable, UUID(transaction_id))
        assert transaction_row is not None
        assert transaction_row.status == "reconciled"
        assert transaction_row.notes == "Updated"


async def test_update_transaction_with_line_edits(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    category_id = await create_category(UUID(budget_id))
    payee_id = await create_payee(UUID(budget_id))

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "notes": "Original",
            "line": {
                "account_id": account_id,
                "category_id": str(category_id),
                "payee_id": str(payee_id),
                "amount_minor": -500,
                "memo": "Original memo",
            },
        },
    )
    assert response.status_code == 201
    payload = response.json()
    transaction_id = payload["id"]
    line_id = payload["lines"][0]["id"]

    new_category_id = await create_category(UUID(budget_id))
    new_payee_id = await create_payee(UUID(budget_id))

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction_id}",
        json={
            "lines": [
                {
                    "line_id": line_id,
                    "amount_minor": -600,
                    "memo": "Updated memo",
                    "category_id": str(new_category_id),
                    "payee_id": str(new_payee_id),
                }
            ]
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    updated_line = updated["lines"][0]
    assert updated_line["id"] == line_id
    assert updated_line["amount_minor"] == -600
    assert updated_line["memo"] == "Updated memo"
    assert updated_line["category_id"] == str(new_category_id)
    assert updated_line["payee_id"] == str(new_payee_id)

    async with get_session_scope() as session:
        line_row = await session.get(TransactionLinesTable, UUID(line_id))
        assert line_row is not None
        assert line_row.amount_minor == -600
        assert line_row.memo == "Updated memo"
        assert line_row.category_id == new_category_id
        assert line_row.payee_id == new_payee_id


async def test_update_transaction_rejects_unknown_line_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    transaction = await create_transaction(async_client, budget_id, account_id)

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction['id']}",
        json={"lines": [{"line_id": str(uuid4()), "memo": "Updated"}]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Line not found."


async def test_update_transaction_rejects_duplicate_line_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    transaction = await create_transaction(async_client, budget_id, account_id)
    line_id = transaction["lines"][0]["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction['id']}",
        json={
            "lines": [
                {"line_id": line_id, "memo": "Updated"},
                {"line_id": line_id, "memo": "Updated again"},
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Duplicate line_id."


async def test_update_transaction_rejects_line_from_another_transaction(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    first = await create_transaction(async_client, budget_id, account_id)
    second = await create_transaction(async_client, budget_id, account_id)
    other_line_id = second["lines"][0]["id"]

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{first['id']}",
        json={"lines": [{"line_id": other_line_id, "memo": "Updated"}]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Line not found."


async def test_update_transaction_rejects_non_transfer_multiple_accounts(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    other_account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = UUID(transaction["id"])

    second_line_id = await add_transaction_line(
        transaction_id, UUID(account_id), amount_minor=-200
    )

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction['id']}",
        json={
            "lines": [
                {"line_id": str(second_line_id), "account_id": other_account_id}
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid transaction lines."


async def test_update_transaction_rejects_invalid_transfer_invariants(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    other_account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = UUID(transaction["id"])

    transfer_line_id = await add_transaction_line(
        transaction_id, UUID(other_account_id), amount_minor=500
    )

    response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction['id']}",
        json={
            "lines": [
                {"line_id": str(transfer_line_id), "amount_minor": 400}
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid transaction lines."


async def test_update_transaction_rejects_import_id_change(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    import_id = f"import-{uuid4()}"

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "import_id": import_id,
            "line": {
                "account_id": account_id,
                "amount_minor": -500,
            },
        },
    )
    assert response.status_code == 201
    transaction_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction_id}",
        json={"import_id": f"import-{uuid4()}"},
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Import id cannot be updated."


async def test_update_transaction_rejects_setting_import_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "line": {
                "account_id": account_id,
                "amount_minor": -500,
            },
        },
    )
    assert response.status_code == 201
    transaction_id = response.json()["id"]

    update_response = await async_client.patch(
        f"/budgets/{budget_id}/transactions/{transaction_id}",
        json={"import_id": f"import-{uuid4()}"},
    )

    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "Import id cannot be updated."


async def test_split_transaction_replaces_lines(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    category_id = await create_category(UUID(budget_id))
    payee_id = await create_payee(UUID(budget_id))

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = UUID(transaction["id"])
    original_line_id = UUID(transaction["lines"][0]["id"])

    extra_line_id = await add_transaction_line(
        transaction_id, UUID(account_id), amount_minor=-200, memo="Old extra"
    )

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/{transaction_id}/split",
        json={
            "lines": [
                {
                    "account_id": account_id,
                    "category_id": str(category_id),
                    "amount_minor": -300,
                    "memo": "Groceries",
                },
                {
                    "account_id": account_id,
                    "payee_id": str(payee_id),
                    "amount_minor": -150,
                    "memo": "Snacks",
                },
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(transaction_id)
    assert payload["lines"]
    assert len(payload["lines"]) == 2

    lines_by_amount = {line["amount_minor"]: line for line in payload["lines"]}
    assert set(lines_by_amount.keys()) == {-300, -150}

    line_minus_300 = lines_by_amount[-300]
    assert line_minus_300["account_id"] == account_id
    assert line_minus_300["category_id"] == str(category_id)
    assert line_minus_300["payee_id"] is None
    assert line_minus_300["memo"] == "Groceries"

    line_minus_150 = lines_by_amount[-150]
    assert line_minus_150["account_id"] == account_id
    assert line_minus_150["category_id"] is None
    assert line_minus_150["payee_id"] == str(payee_id)
    assert line_minus_150["memo"] == "Snacks"

    new_total = sum(line["amount_minor"] for line in payload["lines"])
    assert new_total != -700

    new_line_ids = {UUID(line["id"]) for line in payload["lines"]}
    assert original_line_id not in new_line_ids
    assert extra_line_id not in new_line_ids

    async with get_session_scope() as session:
        result = await session.execute(
            select(TransactionLinesTable).where(
                TransactionLinesTable.transaction_id == transaction_id
            )
        )
        lines = result.scalars().all()
        assert len(lines) == 2
        assert {line.id for line in lines} == new_line_ids


async def test_split_transaction_rejects_transfer(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)
    other_account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = UUID(transaction["id"])

    await add_transaction_line(
        transaction_id, UUID(other_account_id), amount_minor=500
    )

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/{transaction_id}/split",
        json={
            "lines": [
                {
                    "account_id": account_id,
                    "amount_minor": -500,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Transfer transactions cannot be split."


async def test_transfer_creates_two_lines(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    from_account_id = await create_account(async_client, budget_id)
    to_account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/transfer",
        json={
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount_minor": -750,
            "notes": "Move",
            "memo": "Savings",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["budget_id"] == budget_id
    assert payload["status"] == "posted"
    assert payload["notes"] == "Move"
    assert payload["lines"]
    assert len(payload["lines"]) == 2

    lines_by_account = {line["account_id"]: line for line in payload["lines"]}
    assert set(lines_by_account.keys()) == {from_account_id, to_account_id}

    from_line = lines_by_account[from_account_id]
    to_line = lines_by_account[to_account_id]
    assert from_line["amount_minor"] == -750
    assert to_line["amount_minor"] == 750
    assert from_line["category_id"] is None
    assert to_line["category_id"] is None
    assert from_line["payee_id"] is None
    assert to_line["payee_id"] is None
    assert from_line["memo"] == "Savings"
    assert to_line["memo"] == "Savings"
    assert from_line["tag_ids"] == []
    assert to_line["tag_ids"] == []
    assert sum(line["amount_minor"] for line in payload["lines"]) == 0


async def test_transfer_rejects_same_account(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/transfer",
        json={
            "from_account_id": account_id,
            "to_account_id": account_id,
            "amount_minor": -500,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Transfer accounts must be distinct."


async def test_transfer_rejects_zero_amount(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    from_account_id = await create_account(async_client, budget_id)
    to_account_id = await create_account(async_client, budget_id)

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/transfer",
        json={
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount_minor": 0,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Amount must be non-zero."


async def test_transfer_rejects_payee_id(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    from_account_id = await create_account(async_client, budget_id)
    to_account_id = await create_account(async_client, budget_id)
    payee_id = await create_payee(UUID(budget_id))

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/transfer",
        json={
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount_minor": -500,
            "payee_id": str(payee_id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Payee not allowed for transfers."


async def test_delete_transaction_removes_lines(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    transaction = await create_transaction(async_client, budget_id, account_id)
    transaction_id = transaction["id"]

    await add_transaction_line(
        UUID(transaction_id),
        UUID(account_id),
        amount_minor=-250,
        memo="Extra line",
    )

    async with get_session_scope() as session:
        result = await session.execute(
            select(TransactionLinesTable).where(
                TransactionLinesTable.transaction_id == UUID(transaction_id)
            )
        )
        lines = result.scalars().all()
        assert len(lines) == 2

    delete_response = await async_client.delete(
        f"/budgets/{budget_id}/transactions/{transaction_id}"
    )

    assert delete_response.status_code == 204

    async with get_session_scope() as session:
        transaction_row = await session.get(TransactionsTable, UUID(transaction_id))
        assert transaction_row is None

        result = await session.execute(
            select(TransactionLinesTable).where(
                TransactionLinesTable.transaction_id == UUID(transaction_id)
            )
        )
        assert result.scalars().all() == []


async def test_delete_transaction_from_another_budget_returns_404(
    app, async_client
) -> None:
    first_budget_id = await create_budget(async_client)
    second_budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, first_budget_id)

    transaction = await create_transaction(async_client, first_budget_id, account_id)
    transaction_id = transaction["id"]

    delete_response = await async_client.delete(
        f"/budgets/{second_budget_id}/transactions/{transaction_id}"
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Transaction not found."

    async with get_session_scope() as session:
        transaction_row = await session.get(TransactionsTable, UUID(transaction_id))
        assert transaction_row is not None


async def test_bulk_import_transactions_all_new(app, async_client) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    first_import_id = f"import-{uuid4()}"
    second_import_id = f"import-{uuid4()}"

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/import",
        json={
            "transactions": [
                {
                    "import_id": first_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -500,
                    },
                },
                {
                    "import_id": second_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -750,
                    },
                },
            ]
        },
    )

    assert response.status_code == 201
    assert response.json() == {"created_count": 2, "existing_count": 0}

    async with get_session_scope() as session:
        result = await session.execute(
            select(TransactionsTable).where(
                TransactionsTable.budget_id == UUID(budget_id),
                TransactionsTable.import_id.in_(
                    [first_import_id, second_import_id]
                ),
            )
        )
        assert len(result.scalars().all()) == 2


async def test_bulk_import_transactions_skips_existing_import_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    existing_import_id = f"import-{uuid4()}"
    create_response = await async_client.post(
        f"/budgets/{budget_id}/transactions",
        json={
            "import_id": existing_import_id,
            "line": {
                "account_id": account_id,
                "amount_minor": -500,
            },
        },
    )
    assert create_response.status_code == 201

    new_import_id = f"import-{uuid4()}"
    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/import",
        json={
            "transactions": [
                {
                    "import_id": existing_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -600,
                    },
                },
                {
                    "import_id": new_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -700,
                    },
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"created_count": 1, "existing_count": 1}

    async with get_session_scope() as session:
        result = await session.execute(
            select(TransactionsTable).where(
                TransactionsTable.budget_id == UUID(budget_id),
                TransactionsTable.import_id.in_(
                    [existing_import_id, new_import_id]
                ),
            )
        )
        assert len(result.scalars().all()) == 2


async def test_bulk_import_transactions_rejects_duplicate_import_id(
    app, async_client
) -> None:
    budget_id = await create_budget(async_client)
    account_id = await create_account(async_client, budget_id)

    duplicate_import_id = f"import-{uuid4()}"

    response = await async_client.post(
        f"/budgets/{budget_id}/transactions/import",
        json={
            "transactions": [
                {
                    "import_id": duplicate_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -500,
                    },
                },
                {
                    "import_id": duplicate_import_id,
                    "line": {
                        "account_id": account_id,
                        "amount_minor": -600,
                    },
                },
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == [
        {"index": 0, "detail": "Duplicate import_id."},
        {"index": 1, "detail": "Duplicate import_id."},
    ]
