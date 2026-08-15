import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.explanation import CatExplanationModel


async def get_cached(
    db: AsyncSession, analysis_id: uuid.UUID, target_class: str, breed_model_version: str
) -> CatExplanationModel | None:
    """The whole caching contract (Phase 12 spec §13): same analysis,
    same target class, same classifier version → reuse. A different
    classifier version (the model was retrained) simply won't match
    here, so a fresh explanation gets generated instead of silently
    reusing a stale one."""
    stmt = select(CatExplanationModel).where(
        CatExplanationModel.analysis_id == analysis_id,
        CatExplanationModel.target_class == target_class,
        CatExplanationModel.breed_model_version == breed_model_version,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    target_layer: str,
    target_class: str,
    target_class_index: int,
    confidence: float,
    breed_model_version: str,
    heatmap_url: str | None,
    overlay_url: str | None,
    image_width: int,
    image_height: int,
) -> CatExplanationModel:
    row = CatExplanationModel(
        analysis_id=analysis_id,
        target_layer=target_layer,
        target_class=target_class,
        target_class_index=target_class_index,
        confidence=confidence,
        breed_model_version=breed_model_version,
        heatmap_url=heatmap_url,
        overlay_url=overlay_url,
        image_width=image_width,
        image_height=image_height,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
