import uuid

from fastapi import APIRouter, Depends, status

from budget_api.dependencies import require_budget_member
from budget_api.models import (
    Budget,
    Category,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from budget_api.routers.utils import extract_updates
from budget_api.services import CategoriesService

router = APIRouter(prefix="/budgets/{budget_id}/categories")


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to manage categories.")
    ),
    categories_service: CategoriesService = Depends(),
) -> Category:
    return await categories_service.create_category(
        budget=budget,
        name=payload.name,
        parent_id=payload.parent_id,
        is_archived=payload.is_archived,
        sort_order=payload.sort_order,
    )


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    budget: Budget = Depends(require_budget_member("Not authorized to view categories.")),
    categories_service: CategoriesService = Depends(),
) -> list[Category]:
    return await categories_service.list_categories(budget)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to view categories.")),
    categories_service: CategoriesService = Depends(),
) -> Category:
    return await categories_service.get_category(budget, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    budget: Budget = Depends(
        require_budget_member("Not authorized to manage categories.")
    ),
    categories_service: CategoriesService = Depends(),
) -> Category:
    updates = extract_updates(payload)
    return await categories_service.update_category(budget, category_id, updates)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    budget: Budget = Depends(
        require_budget_member("Not authorized to manage categories.")
    ),
    categories_service: CategoriesService = Depends(),
) -> None:
    await categories_service.delete_category(budget, category_id)
