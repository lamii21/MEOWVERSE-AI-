import uuid
from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.schemas.analysis import AnalysisResult

_RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"]
_LEGENDARY_TIER_RARITIES = ("Legendary", "Mythical")

CollectionSort = Literal["newest", "oldest", "rarity", "name"]


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
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            func.lower(CatAnalysisModel.cat_name).like(pattern)
            | func.lower(CatAnalysisModel.breed_label).like(pattern)
        )

    count_stmt = select(func.count(CatAnalysisModel.id)).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = select(CatAnalysisModel).where(*filters)
    if sort == "newest":
        stmt = stmt.order_by(CatAnalysisModel.created_at.desc())
    elif sort == "oldest":
        stmt = stmt.order_by(CatAnalysisModel.created_at.asc())
    elif sort == "name":
        stmt = stmt.order_by(CatAnalysisModel.cat_name.asc())
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
        "favorites_count": favorites_count,
    }


async def get_distinct_color_names(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """Used by the Rainbow Collector achievement — `colors` is JSONB, so
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
