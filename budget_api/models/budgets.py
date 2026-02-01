from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


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
