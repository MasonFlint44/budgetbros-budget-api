from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class User:
    id: uuid.UUID
    email: str
    created_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class Currency:
    code: str
    name: str
    symbol: str | None
    minor_unit: int


class CurrencyResponse(BaseModel):
    code: str
    name: str
    symbol: str | None
    minor_unit: int | None


@dataclass(frozen=True, slots=True)
class Budget:
    id: uuid.UUID
    name: str
    base_currency_code: str
    created_at: datetime


class BudgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_currency_code: str = Field(..., min_length=3, max_length=3)


class BudgetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    base_currency_code: str | None = Field(None, min_length=3, max_length=3)


class BudgetResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_currency_code: str
    created_at: datetime


class BudgetMemberCreate(BaseModel):
    user_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class BudgetMember:
    user_id: uuid.UUID
    email: str
    joined_at: datetime


class BudgetMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    joined_at: datetime


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    cash = "cash"
    loan = "loan"
    investment = "investment"
    asset = "asset"
    liability = "liability"


class AccountCreate(BaseModel):
    budget_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=120)
    type: AccountType = AccountType.checking
    currency_code: str = Field(..., min_length=3, max_length=3)
    is_closed: bool = False


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    type: AccountType | None = None
    currency_code: str | None = Field(None, min_length=3, max_length=3)
    is_closed: bool | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    type: AccountType
    currency_code: str
    is_closed: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Account:
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    type: AccountType
    currency_code: str
    is_closed: bool
    created_at: datetime
