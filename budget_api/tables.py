from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# -----------------------
# Reference data
# -----------------------


class CurrenciesTable(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    minor_unit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=2)

    budgets: Mapped[List["BudgetsTable"]] = relationship(back_populates="base_currency")
    accounts: Mapped[List["AccountsTable"]] = relationship(back_populates="currency")


# -----------------------
# Core identity + sharing
# -----------------------


class UsersTable(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    budget_memberships: Mapped[List["BudgetMembersTable"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    budgets: Mapped[List["BudgetsTable"]] = relationship(
        secondary="budget_members",
        back_populates="users",
        viewonly=True,
    )


class BudgetsTable(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    base_currency_code: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    base_currency: Mapped["CurrenciesTable"] = relationship(back_populates="budgets")

    members: Mapped[List["BudgetMembersTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    users: Mapped[List["UsersTable"]] = relationship(
        secondary="budget_members", back_populates="budgets", viewonly=True
    )

    accounts: Mapped[List["AccountsTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    categories: Mapped[List["CategoriesTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    payees: Mapped[List["PayeesTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["TransactionsTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    tags: Mapped[List["TagsTable"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetMembersTable(Base):
    __tablename__ = "budget_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["UsersTable"] = relationship(back_populates="budget_memberships")
    budget: Mapped["BudgetsTable"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("budget_id", "user_id", name="uq_budget_members_budget_user"),
        Index("ix_budget_members_user_id", "user_id"),
        Index("ix_budget_members_budget_id", "budget_id"),
    )


# -----------------------
# Budget primitives
# -----------------------


class AccountsTable(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Keep as string for flexibility: checking/savings/credit_card/cash/loan/investment/asset/liability
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="checking")

    currency_code: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    budget: Mapped["BudgetsTable"] = relationship(back_populates="accounts")
    currency: Mapped["CurrenciesTable"] = relationship(back_populates="accounts")
    lines: Mapped[List["TransactionLinesTable"]] = relationship(
        back_populates="account"
    )

    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_accounts_budget_name"),
        Index("ix_accounts_budget_id", "budget_id"),
    )


class CategoriesTable(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # "expense" or "income" is usually enough for v1
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="expense")

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    budget: Mapped["BudgetsTable"] = relationship(back_populates="categories")

    parent: Mapped[Optional["CategoriesTable"]] = relationship(
        remote_side="CategoriesTable.id", back_populates="children"
    )
    children: Mapped[List["CategoriesTable"]] = relationship(back_populates="parent")

    lines: Mapped[List["TransactionLinesTable"]] = relationship(
        back_populates="category"
    )

    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_categories_budget_name"),
        Index("ix_categories_budget_id", "budget_id"),
        Index("ix_categories_parent_id", "parent_id"),
    )


class PayeesTable(Base):
    __tablename__ = "payees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    budget: Mapped["BudgetsTable"] = relationship(back_populates="payees")
    lines: Mapped[List["TransactionLinesTable"]] = relationship(back_populates="payee")

    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_payees_budget_name"),
        Index("ix_payees_budget_id", "budget_id"),
    )


# -----------------------
# Transactions + splits + transfers
# -----------------------


class TransactionsTable(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )

    # When the transaction occurred (posted time). Keep as timezone-aware.
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # pending/posted/reconciled/void (string for v1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="posted")

    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # For imports (bank feeds / CSV): unique per budget if provided
    import_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    budget: Mapped["BudgetsTable"] = relationship(back_populates="transactions")
    lines: Mapped[List["TransactionLinesTable"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_transactions_budget_posted_created_id",
            "budget_id",
            desc("posted_at"),
            desc("created_at"),
            desc("id"),
        ),
        UniqueConstraint(
            "budget_id", "import_id", name="uq_transactions_budget_import_id"
        ),
    )


class TransactionLinesTable(Base):
    """
    A single leg of a transaction.

    Conventions that make splits + transfers easy:
    - Splits: multiple lines with the SAME account_id but different category_id and amounts.
    - Transfer: exactly two lines, each with an account_id, and category_id IS NULL for both lines.
    - Expenses/Income: at least one line has a category_id.

    Amount convention:
    - Use signed integer minor units (cents).
    - You can pick your sign convention; a common choice is:
        * Money leaving an account: negative
        * Money entering an account: positive
      Transfers naturally become one negative line + one positive line.
    """

    __tablename__ = "transaction_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Category is nullable to allow transfers
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    payee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payees.id", ondelete="SET NULL"), nullable=True
    )

    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    transaction: Mapped["TransactionsTable"] = relationship(back_populates="lines")
    account: Mapped["AccountsTable"] = relationship(back_populates="lines")
    category: Mapped[Optional["CategoriesTable"]] = relationship(back_populates="lines")
    payee: Mapped[Optional["PayeesTable"]] = relationship(back_populates="lines")

    tags: Mapped[List["TagsTable"]] = relationship(
        secondary="transaction_line_tags",
        back_populates="lines",
        viewonly=True,
    )
    tag_links: Mapped[List["TransactionLineTagsTable"]] = relationship(
        back_populates="line", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # disallow 0-amount lines; helps keep data clean
        CheckConstraint(
            "amount_minor <> 0", name="ck_transaction_lines_nonzero_amount"
        ),
        Index("ix_transaction_lines_transaction_id", "transaction_id"),
        Index("ix_transaction_lines_account_id", "account_id"),
        Index("ix_transaction_lines_category_id", "category_id"),
        Index("ix_transaction_lines_payee_id", "payee_id"),
    )


# -----------------------
# Tags (for filtering)
# -----------------------


class TagsTable(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(60), nullable=False)

    budget: Mapped["BudgetsTable"] = relationship(back_populates="tags")

    lines: Mapped[List["TransactionLinesTable"]] = relationship(
        secondary="transaction_line_tags",
        back_populates="tags",
        viewonly=True,
    )
    line_links: Mapped[List["TransactionLineTagsTable"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("budget_id", "name", name="uq_tags_budget_name"),
        Index("ix_tags_budget_id", "budget_id"),
    )


class TransactionLineTagsTable(Base):
    __tablename__ = "transaction_line_tags"

    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transaction_lines.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    line: Mapped["TransactionLinesTable"] = relationship(back_populates="tag_links")
    tag: Mapped["TagsTable"] = relationship(back_populates="line_links")

    __table_args__ = (Index("ix_transaction_line_tags_tag_id", "tag_id"),)
