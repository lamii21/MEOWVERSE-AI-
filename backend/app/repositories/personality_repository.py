import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import CatPersonalityInterpretationModel, CatPersonalityModel


async def get_cached_personality(
    db: AsyncSession, analysis_id: uuid.UUID, personality_engine_version: str
) -> CatPersonalityModel | None:
    stmt = select(CatPersonalityModel).where(
        CatPersonalityModel.analysis_id == analysis_id,
        CatPersonalityModel.personality_engine_version == personality_engine_version,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_personality(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    personality_engine_version: str,
    archetype_id: str,
    traits: dict,
) -> CatPersonalityModel:
    row = CatPersonalityModel(
        analysis_id=analysis_id,
        personality_engine_version=personality_engine_version,
        archetype_id=archetype_id,
        traits=traits,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_latest_interpretation(
    db: AsyncSession, personality_id: uuid.UUID
) -> CatPersonalityInterpretationModel | None:
    stmt = (
        select(CatPersonalityInterpretationModel)
        .where(CatPersonalityInterpretationModel.personality_id == personality_id)
        .order_by(CatPersonalityInterpretationModel.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_interpretation(
    db: AsyncSession,
    *,
    personality_id: uuid.UUID,
    interpretation_mode: str,
    interpretation_model: str | None,
    interpretation_version: str,
    headline: str,
    description: str,
    catchphrase: str,
    secret_talent: str,
    fictional_job: str,
    fun_fact: str,
) -> CatPersonalityInterpretationModel:
    row = CatPersonalityInterpretationModel(
        personality_id=personality_id,
        interpretation_mode=interpretation_mode,
        interpretation_model=interpretation_model,
        interpretation_version=interpretation_version,
        headline=headline,
        description=description,
        catchphrase=catchphrase,
        secret_talent=secret_talent,
        fictional_job=fictional_job,
        fun_fact=fun_fact,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
