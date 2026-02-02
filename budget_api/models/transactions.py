from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionStatus(str, Enum):
    pending = "pending"
    posted = "posted"
    reconciled = "reconciled"
    void = "void"


class TransactionLineCreate(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    payee_id: uuid.UUID | None = None
    amount_minor: int
    memo: str | None = Field(None, max_length=300)
    tag_ids: list[uuid.UUID] | None = None


class TransactionCreate(BaseModel):
    posted_at: datetime | None = None
    status: str | None = Field(None, max_length=20)
    notes: str | None = Field(None, max_length=500)
    import_id: str | None = Field(None, max_length=200)
    line: TransactionLineCreate


class TransactionSplitCreate(BaseModel):
    lines: list[TransactionLineCreate]


class TransactionLineUpdate(BaseModel):
    line_id: uuid.UUID
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    payee_id: uuid.UUID | None = None
    amount_minor: int | None = None
    memo: str | None = Field(None, max_length=300)
    tag_ids: list[uuid.UUID] | None = None


class TransactionUpdate(BaseModel):
    posted_at: datetime | None = None
    status: str | None = Field(None, max_length=20)
    notes: str | None = Field(None, max_length=500)
    import_id: str | None = Field(None, max_length=200)
    lines: list[TransactionLineUpdate] | None = None


class TransactionLineResponse(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    payee_id: uuid.UUID | None
    amount_minor: int
    memo: str | None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    posted_at: datetime
    status: TransactionStatus
    notes: str | None
    import_id: str | None
    created_at: datetime
    lines: list[TransactionLineResponse] | None = None


@dataclass(frozen=True, slots=True)
class TransactionLine:
    id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    payee_id: uuid.UUID | None
    amount_minor: int
    memo: str | None
    tag_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Transaction:
    id: uuid.UUID
    budget_id: uuid.UUID
    posted_at: datetime
    status: TransactionStatus
    notes: str | None
    import_id: str | None
    created_at: datetime
    lines: list[TransactionLine] | None = None


@dataclass(frozen=True, slots=True)
class TransactionLineDraft:
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    payee_id: uuid.UUID | None
    amount_minor: int
    memo: str | None
    tag_ids: list[uuid.UUID] = field(default_factory=list)
