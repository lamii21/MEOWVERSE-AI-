import uuid
from typing import Literal

from sqlalchemy import Text, case, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.models.story import StoryModel
from app.schemas.analysis import AnalysisResult

_RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"]
_LEGENDARY_TIER_RARITIES = ("Legendary", "Mythical")
# "Rare or higher" — same tiered-threshold pattern as
# _LEGENDARY_TIER_RARITIES, one step down the ladder (Phase 10's Rare
# Hunter achievement).
_RARE_TIER_RARITIES = ("Rare", "Epic", "Legendary", "Mythical")

CollectionSort = Literal[
    "newest", "oldest", "name_asc", "name_desc", "rarity", "breed", "favorite"
]


async def save_analysis(
    db: AsyncSession,
    result: AnalysisResult,
    *,
    user_id: uuid.UUID | None = None,
    image_url: str | None = None,
) -> CatAnalysisModel:
    row = CatAnalysisModel(
        user_id=user_id,
        breed_label=result.breed.label if result.breed else "",
        breed_confidence=result.breed.confidence if result.breed else 0.0,
        breed_mode=result.breed_mode,
        colors=[c.model_dump() for c in result.colors],
        colors_mode=result.colors_mode,
        profile=result.profile.model_dump(),
        profile_mode=result.profile_mode,
        cat_name=result.profile.name,
        rarity=result.profile.rarity,
        image_url=image_url,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> CatAnalysisModel | None:
    return await db.get(CatAnalysisModel, analysis_id)


async def get_public_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> CatAnalysisModel | None:
    row = await db.get(CatAnalysisModel, analysis_id)
    if row is None or not row.is_public:
        return None
    return row


async def get_owned_analysis(
    db: AsyncSession, analysis_id: uuid.UUID, user_id: uuid.UUID
) -> CatAnalysisModel | None:
    """The single ownership-scoped fetch every private-resource operation
    (favorite, unfavorite, unshare, private detail view) goes through —
    returns None for "doesn't exist" and "exists but isn't yours" alike,
    so callers can't distinguish the two and leak existence."""
    row = await db.get(CatAnalysisModel, analysis_id)
    if row is None or row.user_id != user_id:
        return None
    return row


async def set_public(
    db: AsyncSession, analysis_id: uuid.UUID, user_id: uuid.UUID
) -> CatAnalysisModel | None:
    """Flips an analysis to public — the explicit "Share Card" act
    (Phase 8), now ownership-gated (Phase 9): only the owner may share
    their own cat. Idempotent otherwise."""
    row = await get_owned_analysis(db, analysis_id, user_id)
    if row is None:
        return None
    row.is_public = True
    await db.commit()
    await db.refresh(row)
    return row


async def set_private(
    db: AsyncSession, analysis_id: uuid.UUID, user_id: uuid.UUID
) -> CatAnalysisModel | None:
    """Unshare — the inverse of set_public, same ownership gate."""
    row = await get_owned_analysis(db, analysis_id, user_id)
    if row is None:
        return None
    row.is_public = False
    await db.commit()
    await db.refresh(row)
    return row


async def claim_analysis(
    db: AsyncSession, analysis_id: uuid.UUID, user_id: uuid.UUID
) -> CatAnalysisModel | None:
    """The guest-save flow (Phase 9 spec §7-9): a guest analyzes
    anonymously (user_id NULL), later registers/logs in, and clicks
    Save. Only succeeds if the row is currently unowned — an already-owned
    analysis (by this user or anyone else) can't be re-claimed, which is
    what stops one user from "saving" (and thus gaining an ownership
    check pass on) another user's cat by guessing/reusing an id.
    Returns None for "doesn't exist" and "already owned" alike.
    """
    row = await db.get(CatAnalysisModel, analysis_id)
    if row is None or row.user_id is not None:
        return None
    row.user_id = user_id
    await db.commit()
    await db.refresh(row)
    return row


async def set_favorite(
    db: AsyncSession, analysis_id: uuid.UUID, user_id: uuid.UUID, favorite: bool
) -> CatAnalysisModel | None:
    row = await get_owned_analysis(db, analysis_id, user_id)
    if row is None:
        return None
    row.is_favorite = favorite
    await db.commit()
    await db.refresh(row)
    return row


async def list_user_analyses(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    rarity: str | None = None,
    favorites_only: bool = False,
    has_story: bool = False,
    search: str | None = None,
    sort: CollectionSort = "newest",
    page: int = 1,
    page_size: int = 24,
) -> tuple[list[CatAnalysisModel], int]:
    filters = [CatAnalysisModel.user_id == user_id]
    if rarity:
        filters.append(CatAnalysisModel.rarity == rarity)
    if favorites_only:
        filters.append(CatAnalysisModel.is_favorite.is_(True))
    if has_story:
        filters.append(
            exists().where(StoryModel.analysis_id == CatAnalysisModel.id)
        )
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            func.lower(CatAnalysisModel.cat_name).like(pattern)
            | func.lower(CatAnalysisModel.breed_label).like(pattern)
            | func.lower(cast(CatAnalysisModel.colors, Text)).like(pattern)
        )

    count_stmt = select(func.count(CatAnalysisModel.id)).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = select(CatAnalysisModel).where(*filters)
    if sort == "newest":
        stmt = stmt.order_by(CatAnalysisModel.created_at.desc())
    elif sort == "oldest":
        stmt = stmt.order_by(CatAnalysisModel.created_at.asc())
    elif sort == "name_asc":
        stmt = stmt.order_by(CatAnalysisModel.cat_name.asc())
    elif sort == "name_desc":
        stmt = stmt.order_by(CatAnalysisModel.cat_name.desc())
    elif sort == "breed":
        stmt = stmt.order_by(
            CatAnalysisModel.breed_label.asc(), CatAnalysisModel.created_at.desc()
        )
    elif sort == "favorite":
        stmt = stmt.order_by(
            CatAnalysisModel.is_favorite.desc(), CatAnalysisModel.created_at.desc()
        )
    elif sort == "rarity":
        rarity_rank = case(
            {name: i for i, name in enumerate(_RARITY_ORDER)},
            value=CatAnalysisModel.rarity,
            else_=-1,
        )
        stmt = stmt.order_by(rarity_rank.desc(), CatAnalysisModel.created_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


async def get_user_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    total = (
        await db.execute(
            select(func.count()).where(CatAnalysisModel.user_id == user_id)
        )
    ).scalar_one()

    favorite_breed_row = (
        await db.execute(
            select(CatAnalysisModel.breed_label, func.count().label("n"))
            .where(CatAnalysisModel.user_id == user_id)
            .group_by(CatAnalysisModel.breed_label)
            .order_by(func.count().desc())
            .limit(1)
        )
    ).first()

    legendary_count = (
        await db.execute(
            select(func.count()).where(
                CatAnalysisModel.user_id == user_id,
                CatAnalysisModel.rarity.in_(_LEGENDARY_TIER_RARITIES),
            )
        )
    ).scalar_one()

    rare_count = (
        await db.execute(
            select(func.count()).where(
                CatAnalysisModel.user_id == user_id,
                CatAnalysisModel.rarity.in_(_RARE_TIER_RARITIES),
            )
        )
    ).scalar_one()

    favorites_count = (
        await db.execute(
            select(func.count()).where(
                CatAnalysisModel.user_id == user_id, CatAnalysisModel.is_favorite.is_(True)
            )
        )
    ).scalar_one()

    dominant_colors = (
        await db.execute(
            select(CatAnalysisModel.colors).where(CatAnalysisModel.user_id == user_id)
        )
    ).scalars().all()
    color_counts: dict[str, int] = {}
    for palette in dominant_colors:
        if palette:
            color_counts[palette[0]["name"]] = color_counts.get(palette[0]["name"], 0) + 1
    most_common_color = max(color_counts, key=color_counts.get) if color_counts else None

    return {
        "total_cats": total,
        "favorite_breed": favorite_breed_row[0] if favorite_breed_row else None,
        "most_common_color": most_common_color,
        "legendary_count": legendary_count,
        "rare_count": rare_count,
        "favorites_count": favorites_count,
    }


async def get_distinct_color_names(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Used by the Color Collector achievement — `colors` is JSONB, so
    this pulls the raw rows and extracts names in Python rather than
    trying to express a JSONB-array-of-objects DISTINCT in SQL."""
    rows = (
        await db.execute(
            select(CatAnalysisModel.colors).where(CatAnalysisModel.user_id == user_id)
        )
    ).scalars().all()
    names: set[str] = set()
    for palette in rows:
        for swatch in palette:
            names.add(swatch["name"])
    return names


async def get_rarity_distribution(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    """Zero-filled across all six tiers (Phase 10 spec §20/21: "define
    rarity distribution clearly") — a tier the user hasn't discovered
    yet reads as 0, not as a missing key the frontend has to guard for.
    """
    rows = (
        await db.execute(
            select(CatAnalysisModel.rarity, func.count())
            .where(CatAnalysisModel.user_id == user_id)
            .group_by(CatAnalysisModel.rarity)
        )
    ).all()
    counts = {rarity: n for rarity, n in rows}
    return {tier: counts.get(tier, 0) for tier in _RARITY_ORDER}


async def get_discovered_breeds(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Every distinct breed_label this user has ever gotten, with no
    filtering against the canonical breed universe — the caller (breed
    catalog / completion-percentage logic) decides which of these count
    toward "completion." See app/services/breed_catalog.py."""
    rows = (
        await db.execute(
            select(CatAnalysisModel.breed_label)
            .where(CatAnalysisModel.user_id == user_id)
            .distinct()
        )
    ).scalars().all()
    return set(rows)


async def get_breed_discovery_stats(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[str, dict]:
    """Per-breed aggregate stats for every breed this user has
    analyzed at least once: count, best (highest) confidence, and the
    most recent discovery date. Powers the Breed Explorer (Phase 10
    spec §10) — merging against the full canonical breed list (for the
    "undiscovered, still locked" rows) is the caller's job, in
    app/services/collection_service.py, since this repository layer
    shouldn't need to know about the ML breed-catalog module.
    """
    rows = (
        await db.execute(
            select(
                CatAnalysisModel.breed_label,
                func.count().label("count"),
                func.max(CatAnalysisModel.breed_confidence).label("best_confidence"),
                func.max(CatAnalysisModel.created_at).label("latest_discovery"),
            )
            .where(CatAnalysisModel.user_id == user_id)
            .group_by(CatAnalysisModel.breed_label)
        )
    ).all()
    return {
        breed: {"count": count, "best_confidence": best_confidence, "latest_discovery": latest}
        for breed, count, best_confidence, latest in rows
    }


async def is_first_of_breed(
    db: AsyncSession, user_id: uuid.UUID, breed_label: str, exclude_id: uuid.UUID
) -> bool:
    """Whether `exclude_id` (the analysis just created/claimed) is the
    *first* time this user has ever gotten this exact breed_label —
    drives the "New breed discovered!" toast (spec §19). Deliberately
    recomputed fresh from the real rows every time rather than a stored
    flag, so it can never desync from what actually happened."""
    stmt = select(func.count()).where(
        CatAnalysisModel.user_id == user_id,
        CatAnalysisModel.breed_label == breed_label,
        CatAnalysisModel.id != exclude_id,
    )
    return (await db.execute(stmt)).scalar_one() == 0


async def is_first_of_rarity(
    db: AsyncSession, user_id: uuid.UUID, rarity: str, exclude_id: uuid.UUID
) -> bool:
    """Same idea as `is_first_of_breed`, for rarity tiers (spec §19's
    "New rarity discovered!" toast)."""
    stmt = select(func.count()).where(
        CatAnalysisModel.user_id == user_id,
        CatAnalysisModel.rarity == rarity,
        CatAnalysisModel.id != exclude_id,
    )
    return (await db.execute(stmt)).scalar_one() == 0
