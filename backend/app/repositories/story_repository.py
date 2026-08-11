import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    return await db.get(StoryModel, story_id)


async def count_stories(db: AsyncSession, analysis_id: uuid.UUID, style: StoryStyle) -> int:
    stmt = select(func.count(StoryModel.id)).where(
        StoryModel.analysis_id == analysis_id, StoryModel.style == style.value
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def set_public(db: AsyncSession, story_id: uuid.UUID) -> StoryModel | None:
    """Flips a story to public — the explicit "Share" act (Phase 7 §17).
    Never automatic; there is no path that calls this besides the user
    pressing Share on a story they just generated."""
    row = await db.get(StoryModel, story_id)
    if row is None:
        return None
    row.is_public = True
    await db.commit()
    await db.refresh(row)
    return row
