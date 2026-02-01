from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
    name: str = Field(..., min_length=1, max_length=120)
    type: AccountType = AccountType.checking
    currency_code: str = Field(..., min_length=3, max_length=3)
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    type: AccountType | None = None
    currency_code: str | None = Field(None, min_length=3, max_length=3)
    is_active: bool | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    type: AccountType
    currency_code: str
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Account:
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    type: AccountType
    currency_code: str
    is_active: bool
    created_at: datetime
