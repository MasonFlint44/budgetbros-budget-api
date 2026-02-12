from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_archived: bool = False
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    is_archived: bool | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    is_archived: bool
    sort_order: int


@dataclass(frozen=True, slots=True)
class Category:
    id: uuid.UUID
    budget_id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    is_archived: bool
    sort_order: int
