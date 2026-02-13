from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field


class PayeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)


class PayeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)


class PayeeResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str


@dataclass(frozen=True, slots=True)
class Payee:
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
