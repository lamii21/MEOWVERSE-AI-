import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portrait import CatPortraitModel


async def create_pending(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    user_id: uuid.UUID | None,
    style_id: str,
    customization: str | None,
    generation_identity_hash: str,
    provider: str,
    prompt_version: str,
) -> CatPortraitModel:
    row = CatPortraitModel(
        analysis_id=analysis_id,
        user_id=user_id,
        style_id=style_id,
        customization=customization,
        generation_identity_hash=generation_identity_hash,
        provider=provider,
        model=None,
        prompt_version=prompt_version,
        status="pending",
        image_url=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def mark_succeeded(
    db: AsyncSession, row: CatPortraitModel, *, image_url: str, model: str
) -> CatPortraitModel:
    row.status = "succeeded"
    row.image_url = image_url
    row.model = model
    row.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def mark_failed(
    db: AsyncSession, row: CatPortraitModel, *, error_code: str, error_message: str
) -> CatPortraitModel:
    row.status = "failed"
    row.error_code = error_code
    row.error_message = error_message
    row.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def find_reusable(
    db: AsyncSession, *, analysis_id: uuid.UUID, generation_identity_hash: str
) -> CatPortraitModel | None:
    """The soft duplicate-generation dedup (spec §23): the most recent
    *succeeded* portrait matching this exact generation identity. A
    caller explicitly requesting "Generate Again" (`force_new=True`)
    skips this lookup entirely — see portrait_service.py."""
    stmt = (
        select(CatPortraitModel)
        .where(
            CatPortraitModel.analysis_id == analysis_id,
            CatPortraitModel.generation_identity_hash == generation_identity_hash,
            CatPortraitModel.status == "succeeded",
        )
        .order_by(CatPortraitModel.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_for_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> list[CatPortraitModel]:
    stmt = (
        select(CatPortraitModel)
        .where(CatPortraitModel.analysis_id == analysis_id)
        .order_by(CatPortraitModel.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_public(db: AsyncSession, portrait_id: uuid.UUID) -> CatPortraitModel | None:
    row = await db.get(CatPortraitModel, portrait_id)
    if row is None or not row.is_public:
        return None
    return row


async def get_owned(
    db: AsyncSession, portrait_id: uuid.UUID, user_id: uuid.UUID
) -> CatPortraitModel | None:
    row = await db.get(CatPortraitModel, portrait_id)
    if row is None or row.user_id != user_id:
        return None
    return row


async def set_public(
    db: AsyncSession, portrait_id: uuid.UUID, user_id: uuid.UUID
) -> CatPortraitModel | None:
    row = await get_owned(db, portrait_id, user_id)
    if row is None or row.status != "succeeded":
        return None
    row.is_public = True
    await db.commit()
    await db.refresh(row)
    return row


async def set_private(
    db: AsyncSession, portrait_id: uuid.UUID, user_id: uuid.UUID
) -> CatPortraitModel | None:
    row = await get_owned(db, portrait_id, user_id)
    if row is None:
        return None
    row.is_public = False
    await db.commit()
    await db.refresh(row)
    return row


async def count_user_portraits(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Powers the "First Portrait" achievement (spec §37) — every
    succeeded generation for this user, real rows only."""
    stmt = select(func.count(CatPortraitModel.id)).where(
        CatPortraitModel.user_id == user_id, CatPortraitModel.status == "succeeded"
    )
    return (await db.execute(stmt)).scalar_one()


async def count_distinct_user_styles(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Powers the "Style Collector" achievement (spec §37)."""
    stmt = select(func.count(func.distinct(CatPortraitModel.style_id))).where(
        CatPortraitModel.user_id == user_id, CatPortraitModel.status == "succeeded"
    )
    return (await db.execute(stmt)).scalar_one()


async def get_analysis_ids_with_public_portraits(
    db: AsyncSession, analysis_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Batched, N+1-avoiding lookup (same shape as
    `story_repository.get_analysis_ids_with_public_stories`) for the
    `/explore` discovery card's "has AI portrait" indicator — succeeded
    AND public only, so a private or failed portrait is never implied
    to exist via a public discovery card (Phase 15 spec §5/§19)."""
    if not analysis_ids:
        return set()
    stmt = (
        select(CatPortraitModel.analysis_id)
        .where(
            CatPortraitModel.analysis_id.in_(analysis_ids),
            CatPortraitModel.is_public.is_(True),
            CatPortraitModel.status == "succeeded",
        )
        .distinct()
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)
