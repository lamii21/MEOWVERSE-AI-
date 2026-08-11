from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.analyses import analysis_row_to_result
from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.models.user import UserModel
from app.repositories.analysis_repository import list_user_analyses
from app.schemas.collection import AchievementOut, CollectionPage, CollectionStats
from app.services.collection_service import get_stats, sync_and_list_achievements

router = APIRouter(prefix="/api/v1/me", tags=["collection"])

_VALID_RARITIES = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"}


@router.get("/collection", response_model=CollectionPage)
async def get_my_collection(
    rarity: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=100),
    sort: Literal["newest", "oldest", "rarity", "name"] = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> CollectionPage:
    if rarity is not None and rarity not in _VALID_RARITIES:
        rarity = None  # an unrecognized filter value just yields no match, not a 422

    items, total = await list_user_analyses(
        db,
        user.id,
        rarity=rarity,
        favorites_only=favorites_only,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return CollectionPage(
        items=[analysis_row_to_result(row, viewer_is_owner=True) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=CollectionStats)
async def get_my_stats(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> CollectionStats:
    return await get_stats(db, user.id)


@router.get("/achievements", response_model=list[AchievementOut])
async def get_my_achievements(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[AchievementOut]:
    return await sync_and_list_achievements(db, user.id)
