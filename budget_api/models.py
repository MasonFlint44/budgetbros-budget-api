from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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
