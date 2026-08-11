from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.analyses import analysis_row_to_result
from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.models.user import UserModel
from app.repositories.analysis_repository import CollectionSort, list_user_analyses
from app.repositories.story_repository import get_analysis_ids_with_stories
from app.schemas.collection import (
    AchievementOut,
    BreedDiscoveryOut,
    CollectionPage,
    CollectionStats,
    ProgressOut,
)
from app.services.collection_service import (
    get_breed_explorer,
    get_progress,
    get_stats,
    sync_and_list_achievements,
)

router = APIRouter(prefix="/api/v1/me", tags=["collection"])

_VALID_RARITIES = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"}


@router.get("/collection", response_model=CollectionPage)
async def get_my_collection(
    rarity: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
    has_story: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=100),
    sort: CollectionSort = Query(default="newest"),  # noqa: B008
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
        has_story=has_story,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    # One batched query for the whole page rather than one per row —
    # see get_analysis_ids_with_stories's docstring (Phase 10 spec §27:
    # avoid N+1 queries in the collection view).
    ids_with_stories = await get_analysis_ids_with_stories(db, [row.id for row in items])
    return CollectionPage(
        items=[
            analysis_row_to_result(row, viewer_is_owner=True, has_story=row.id in ids_with_stories)
            for row in items
        ],
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


@router.get("/breeds", response_model=list[BreedDiscoveryOut])
async def get_my_breeds(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BreedDiscoveryOut]:
    """Powers the Breed Explorer (Phase 10 spec §10). Note this
    endpoint lives under the established /api/v1/me/ prefix (Phase 9)
    rather than the spec's suggested standalone
    /api/v1/collection/breeds — every "current user" resource
    (collection, stats, achievements, now breeds/progress) shares one
    namespace instead of forking a second for this phase alone."""
    return await get_breed_explorer(db, user.id)


@router.get("/progress", response_model=ProgressOut)
async def get_my_progress(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> ProgressOut:
    return await get_progress(db, user.id)
