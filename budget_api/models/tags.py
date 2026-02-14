from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=60)


class TagResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str


@dataclass(frozen=True, slots=True)
class Tag:
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
