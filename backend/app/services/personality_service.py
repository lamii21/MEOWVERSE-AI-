import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import CatAnalysisModel
from app.models.personality import CatPersonalityInterpretationModel, CatPersonalityModel
from app.repositories import personality_repository
from app.repositories.analysis_repository import get_owned_analysis, get_public_analysis
from app.schemas.common import ColorSwatch
from app.schemas.personality import (
    CatPersonalityResponse,
    PersonalityArchetypeOut,
    PersonalityInterpretation,
    PersonalityTraitScore,
)
from app.schemas.profile import CatSignals
from app.services.personality_interpretation_service import (
    INTERPRETATION_VERSION,
    generate_interpretation,
)
from app.services.personality_scoring import (
    PERSONALITY_ENGINE_VERSION,
    compute_traits,
    get_archetype,
    select_archetype,
)


class SourceAnalysisNotVisibleError(Exception):
    """The source analysis doesn't exist, or isn't visible to this
    caller — surfaced by the API layer as 404. Same anti-enumeration
    principle as every other ownership check in this codebase."""


async def _resolve_visible_source(
    db: AsyncSession, analysis_id: uuid.UUID, viewer_user_id: uuid.UUID | None
) -> CatAnalysisModel:
    source = await get_public_analysis(db, analysis_id)
    if source is None and viewer_user_id is not None:
        source = await get_owned_analysis(db, analysis_id, viewer_user_id)
    if source is None:
        raise SourceAnalysisNotVisibleError(str(analysis_id))
    return source


async def _get_or_create_personality(
    db: AsyncSession, analysis: CatAnalysisModel
) -> CatPersonalityModel:
    cached = await personality_repository.get_cached_personality(
        db, analysis.id, PERSONALITY_ENGINE_VERSION
    )
    if cached is not None:
        return cached

    traits = compute_traits(
        analysis_id=str(analysis.id),
        breed_label=analysis.breed_label,
        breed_confidence=analysis.breed_confidence,
        colors=analysis.colors,
    )
    archetype = select_archetype(traits)
    return await personality_repository.create_personality(
        db,
        analysis_id=analysis.id,
        personality_engine_version=PERSONALITY_ENGINE_VERSION,
        archetype_id=archetype.id,
        traits=traits,
    )


async def _generate_and_store_interpretation(
    db: AsyncSession, personality: CatPersonalityModel, analysis: CatAnalysisModel
) -> CatPersonalityInterpretationModel:
    archetype = get_archetype(personality.archetype_id)
    assert archetype is not None  # archetype_id is only ever written from ARCHETYPES

    signals = CatSignals(
        breed=analysis.breed_label,
        breed_confidence=analysis.breed_confidence,
        breed_mode=analysis.breed_mode,
        colors=[ColorSwatch.model_validate(c) for c in analysis.colors],
        colors_mode=analysis.colors_mode,
    )
    trait_levels = {trait: data["level"] for trait, data in personality.traits.items()}

    interpretation, mode, model = await generate_interpretation(
        signals=signals,
        archetype=archetype,
        trait_levels=trait_levels,
        rarity=analysis.rarity,
    )
    return await personality_repository.create_interpretation(
        db,
        personality_id=personality.id,
        interpretation_mode=mode,
        interpretation_model=model,
        interpretation_version=INTERPRETATION_VERSION,
        headline=interpretation.headline,
        description=interpretation.description,
        catchphrase=interpretation.catchphrase,
        secret_talent=interpretation.secret_talent,
        fictional_job=interpretation.fictional_job,
        fun_fact=interpretation.fun_fact,
    )


def _build_response(
    personality: CatPersonalityModel,
    interpretation: CatPersonalityInterpretationModel,
    *,
    interpretation_cached: bool,
) -> CatPersonalityResponse:
    archetype = get_archetype(personality.archetype_id)
    assert archetype is not None

    return CatPersonalityResponse(
        id=personality.id,
        analysis_id=personality.analysis_id,
        personality_engine_version=personality.personality_engine_version,
        archetype=PersonalityArchetypeOut(
            id=archetype.id,
            name=archetype.name,
            emoji=archetype.emoji,
            short_description=archetype.short_description,
            long_description=archetype.long_description,
            theme_token=archetype.theme_token,
        ),
        traits={
            trait: PersonalityTraitScore.model_validate(data)
            for trait, data in personality.traits.items()
        },
        created_at=personality.created_at,
        interpretation_mode=interpretation.interpretation_mode,
        interpretation_model=interpretation.interpretation_model,
        interpretation_version=interpretation.interpretation_version,
        interpretation=PersonalityInterpretation(
            headline=interpretation.headline,
            description=interpretation.description,
            catchphrase=interpretation.catchphrase,
            secret_talent=interpretation.secret_talent,
            fictional_job=interpretation.fictional_job,
            fun_fact=interpretation.fun_fact,
        ),
        interpretation_created_at=interpretation.created_at,
        interpretation_cached=interpretation_cached,
    )


async def get_personality(
    db: AsyncSession, analysis_id: uuid.UUID, *, viewer_user_id: uuid.UUID | None
) -> CatPersonalityResponse:
    """`GET /api/v1/analyses/{id}/personality` — read-only visibility
    rule (public OR owned), same as every other analysis-scoped
    endpoint. Auto-computes the structured personality (cheap,
    deterministic) and auto-generates the interpretation (may call the
    LLM) on first access, then serves the cached versions of both on
    every subsequent call."""
    source = await _resolve_visible_source(db, analysis_id, viewer_user_id)
    personality = await _get_or_create_personality(db, source)

    interpretation = await personality_repository.get_latest_interpretation(db, personality.id)
    cached = interpretation is not None
    if interpretation is None:
        interpretation = await _generate_and_store_interpretation(db, personality, source)

    return _build_response(personality, interpretation, interpretation_cached=cached)


async def regenerate_interpretation(
    db: AsyncSession, analysis_id: uuid.UUID, *, owner_user_id: uuid.UUID
) -> CatPersonalityResponse:
    """`POST /api/v1/analyses/{id}/personality/regenerate` — requires
    genuine ownership (not just "public OR owned"), deliberately
    stricter than the read path: this is a mutating, potentially
    LLM-cost-bearing action, so a stranger who can merely *view* a
    public cat must not be able to trigger new generations against it.
    Never touches the structured `CatPersonalityModel` row — the
    numeric traits and archetype are byte-identical before and after."""
    source = await get_owned_analysis(db, analysis_id, owner_user_id)
    if source is None:
        raise SourceAnalysisNotVisibleError(str(analysis_id))

    personality = await _get_or_create_personality(db, source)
    interpretation = await _generate_and_store_interpretation(db, personality, source)
    return _build_response(personality, interpretation, interpretation_cached=False)
