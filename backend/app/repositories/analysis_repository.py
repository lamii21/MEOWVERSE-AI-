import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.schemas.analysis import AnalysisResult


async def save_analysis(db: AsyncSession, result: AnalysisResult) -> CatAnalysisModel:
    row = CatAnalysisModel(
        breed_label=result.breed.label if result.breed else "",
        breed_confidence=result.breed.confidence if result.breed else 0.0,
        breed_mode=result.breed_mode,
        colors=[c.model_dump() for c in result.colors],
        colors_mode=result.colors_mode,
        profile=result.profile.model_dump(),
        profile_mode=result.profile_mode,
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


async def set_public(db: AsyncSession, analysis_id: uuid.UUID) -> CatAnalysisModel | None:
    """Flips an analysis to public — the explicit "Share Card" act
    (Phase 8). Never automatic, same contract as story_repository.set_public."""
    row = await db.get(CatAnalysisModel, analysis_id)
    if row is None:
        return None
    row.is_public = True
    await db.commit()
    await db.refresh(row)
    return row
