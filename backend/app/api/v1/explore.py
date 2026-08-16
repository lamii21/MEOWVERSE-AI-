from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import enforce_explore_rate_limit
from app.schemas.explore import (
    BreedExplorerOut,
    ColorExplorerOut,
    ExploreCatsPage,
    ExploreSort,
    FeaturedCatsResponse,
    PersonalityArchetypeExplorerOut,
)
from app.services.explore_service import (
    get_breed_explorer,
    get_color_explorer,
    get_featured_cats,
    get_personality_explorer,
    list_explore_cats,
)

router = APIRouter(prefix="/api/v1/explore", tags=["explore"])


@router.get(
    "/cats",
    response_model=ExploreCatsPage,
    dependencies=[Depends(enforce_explore_rate_limit)],
)
async def explore_cats(
    breed: str | None = Query(default=None, max_length=100),
    rarity: str | None = Query(default=None),
    archetype: str | None = Query(default=None, max_length=40),
    color: str | None = Query(default=None, max_length=40),
    has_story: bool = Query(default=False),
    has_portrait: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=100),
    sort: ExploreSort = Query(default="newest"),  # noqa: B008
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ExploreCatsPage:
    """The MeowVerse Cat Universe's main public listing (Phase 15) —
    guest-accessible (discovery is the whole point), scoped to public
    cats only at the SQL/repository level (spec §28), paginated (spec
    §4), with a small, honest set of filters/sorts (spec §7-9: no
    fabricated metrics)."""
    return await list_explore_cats(
        db,
        breed=breed,
        rarity=rarity,
        archetype=archetype,
        color=color,
        has_public_story=has_story,
        has_public_portrait=has_portrait,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/featured",
    response_model=FeaturedCatsResponse,
    dependencies=[Depends(enforce_explore_rate_limit)],
)
async def explore_featured(db: AsyncSession = Depends(get_db)) -> FeaturedCatsResponse:  # noqa: B008
    """A deterministic, documented featured selection (spec §10) — see
    `explore_service._featured_score`. Never randomized."""
    return await get_featured_cats(db)


@router.get(
    "/breeds",
    response_model=list[BreedExplorerOut],
    dependencies=[Depends(enforce_explore_rate_limit)],
)
async def explore_breeds(db: AsyncSession = Depends(get_db)) -> list[BreedExplorerOut]:  # noqa: B008
    """Breed Explorer (spec §12) — the canonical breed universe
    (Phase 10's breed_catalog) merged with real public-cat counts."""
    return await get_breed_explorer(db)


@router.get(
    "/personalities",
    response_model=list[PersonalityArchetypeExplorerOut],
    dependencies=[Depends(enforce_explore_rate_limit)],
)
async def explore_personalities(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PersonalityArchetypeExplorerOut]:
    """Personality Explorer (spec §13) — the 10 Phase 13 archetypes
    with real public-cat counts/examples. Never claims a scientific
    classification (see each entry's `disclaimer` field)."""
    return await get_personality_explorer(db)


@router.get(
    "/colors",
    response_model=list[ColorExplorerOut],
    dependencies=[Depends(enforce_explore_rate_limit)],
)
async def explore_colors(db: AsyncSession = Depends(get_db)) -> list[ColorExplorerOut]:  # noqa: B008
    """Color Explorer (spec §14) — groups public cats by dominant fur
    color, reusing Phase 5's real analyzed swatches."""
    return await get_color_explorer(db)
