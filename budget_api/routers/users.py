from fastapi import APIRouter, Depends

from budget_api.auth import get_or_create_current_user
from budget_api.models import User, UserResponse

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_or_create_current_user),
) -> User:
    return current_user
