import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.models.story import StoryModel
from app.schemas.story import CatStory, StoryStyle


async def save_story(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    style: StoryStyle,
    story: CatStory,
    story_mode: str,
    provider: str,
    model: str | None,
) -> StoryModel:
    row = StoryModel(
        analysis_id=analysis_id,
        style=style.value,
        title=story.title,
        story=story.model_dump(),
        story_mode=story_mode,
        provider=provider,
        model=model,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_latest_story(
    db: AsyncSession, analysis_id: uuid.UUID, style: StoryStyle
) -> StoryModel | None:
    stmt = (
        select(StoryModel)
        .where(StoryModel.analysis_id == analysis_id, StoryModel.style == style.value)
        .order_by(StoryModel.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_story(db: AsyncSession, story_id: uuid.UUID) -> StoryModel | None:
    """Unfiltered — internal use only (e.g. building a public/owner
    view where the caller applies its own visibility check right after).
    Prefer `get_public_story`/`get_owned_story` at API boundaries so the
    filter can't be forgotten by a future caller."""
    return await db.get(StoryModel, story_id)


async def get_public_story(db: AsyncSession, story_id: uuid.UUID) -> StoryModel | None:
    row = await db.get(StoryModel, story_id)
    if row is None or not row.is_public:
        return None
    return row


async def get_owned_story(
    db: AsyncSession, story_id: uuid.UUID, user_id: uuid.UUID
) -> StoryModel | None:
    """A story has no `user_id` of its own — ownership is inherited from
    its parent analysis, so this joins through `cat_analyses`."""
    stmt = (
        select(StoryModel)
        .join(CatAnalysisModel, StoryModel.analysis_id == CatAnalysisModel.id)
        .where(StoryModel.id == story_id, CatAnalysisModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_stories(db: AsyncSession, analysis_id: uuid.UUID, style: StoryStyle) -> int:
    stmt = select(func.count(StoryModel.id)).where(
        StoryModel.analysis_id == analysis_id, StoryModel.style == style.value
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_user_stories(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count(StoryModel.id))
        .join(CatAnalysisModel, StoryModel.analysis_id == CatAnalysisModel.id)
        .where(CatAnalysisModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def has_any_story(db: AsyncSession, analysis_id: uuid.UUID) -> bool:
    stmt = select(func.count(StoryModel.id)).where(StoryModel.analysis_id == analysis_id)
    return (await db.execute(stmt)).scalar_one() > 0


async def get_analysis_ids_with_stories(
    db: AsyncSession, analysis_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Batched version of `has_any_story` for a page of results — one
    query for the whole page rather than one per row (Phase 10 spec
    §27: avoid N+1 queries in the collection view)."""
    if not analysis_ids:
        return set()
    stmt = (
        select(StoryModel.analysis_id).where(StoryModel.analysis_id.in_(analysis_ids)).distinct()
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def has_story_of_style(db: AsyncSession, user_id: uuid.UUID, style: str) -> bool:
    """Powers the Dream Keeper achievement (generate a Dreamy &
    Emotional story) — a real query against the user's own stories,
    joined through their owned analyses, never a client-asserted flag.
    """
    stmt = (
        select(func.count(StoryModel.id))
        .join(CatAnalysisModel, StoryModel.analysis_id == CatAnalysisModel.id)
        .where(CatAnalysisModel.user_id == user_id, StoryModel.style == style)
    )
    result = await db.execute(stmt)
    return result.scalar_one() > 0


async def set_public(
    db: AsyncSession, story_id: uuid.UUID, user_id: uuid.UUID
) -> StoryModel | None:
    """Flips a story to public — the explicit "Share" act (Phase 7 §17),
    now ownership-gated (Phase 9): only the owner of the parent analysis
    may share its story."""
    row = await get_owned_story(db, story_id, user_id)
    if row is None:
        return None
    row.is_public = True
    await db.commit()
    await db.refresh(row)
    return row


async def set_private(
    db: AsyncSession, story_id: uuid.UUID, user_id: uuid.UUID
) -> StoryModel | None:
    row = await get_owned_story(db, story_id, user_id)
    if row is None:
        return None
    row.is_public = False
    await db.commit()
    await db.refresh(row)
    return row


async def get_analysis_ids_with_public_stories(
    db: AsyncSession, analysis_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Same batched, N+1-avoiding shape as `get_analysis_ids_with_stories`
    above, but scoped to `is_public` stories only — used for the
    `/explore` discovery card's "has story" indicator, which must never
    imply a *private* story exists just because some story does (Phase
    15 spec §5: never leak the existence of private content)."""
    if not analysis_ids:
        return set()
    stmt = (
        select(StoryModel.analysis_id)
        .where(StoryModel.analysis_id.in_(analysis_ids), StoryModel.is_public.is_(True))
        .distinct()
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)
