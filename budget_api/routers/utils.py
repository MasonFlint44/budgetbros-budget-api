from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import BaseModel


def reject_null_updates(updates: dict[str, object]) -> None:
    null_fields = [key for key, value in updates.items() if value is None]
    if null_fields:
        field_list = ", ".join(sorted(null_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Fields cannot be null: {field_list}",
        )


def extract_updates(
    payload: BaseModel, *, empty_detail: str = "No fields to update."
) -> dict[str, object]:
    updates = payload.model_dump(exclude_unset=True)
    reject_null_updates(updates)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=empty_detail,
        )
    return updates
