import uuid

from fastapi import APIRouter, Depends, status

from budget_api.dependencies import require_budget_member
from budget_api.models import Budget, Tag, TagCreate, TagResponse, TagUpdate
from budget_api.routers.utils import extract_updates
from budget_api.services import TagsService

router = APIRouter(prefix="/budgets/{budget_id}/tags")


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage tags.")),
    tags_service: TagsService = Depends(),
) -> Tag:
    return await tags_service.create_tag(
        budget=budget,
        name=payload.name,
    )


@router.get("", response_model=list[TagResponse])
async def list_tags(
    budget: Budget = Depends(require_budget_member("Not authorized to view tags.")),
    tags_service: TagsService = Depends(),
) -> list[Tag]:
    return await tags_service.list_tags(budget)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to view tags.")),
    tags_service: TagsService = Depends(),
) -> Tag:
    return await tags_service.get_tag(budget, tag_id)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: uuid.UUID,
    payload: TagUpdate,
    budget: Budget = Depends(require_budget_member("Not authorized to manage tags.")),
    tags_service: TagsService = Depends(),
) -> Tag:
    updates = extract_updates(payload)
    return await tags_service.update_tag(budget, tag_id, updates)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    budget: Budget = Depends(require_budget_member("Not authorized to manage tags.")),
    tags_service: TagsService = Depends(),
) -> None:
    await tags_service.delete_tag(budget, tag_id)
