from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


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
