import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.models.user import UserModel
from app.schemas.personality import CatPersonalityResponse
from app.services.personality_service import (
    SourceAnalysisNotVisibleError,
    get_personality,
    regenerate_interpretation,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["personality"])


@router.get(
    "/{analysis_id}/personality",
    response_model=CatPersonalityResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_cat_personality(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> CatPersonalityResponse:
    """The MeowVerse Cat Personality Engine (Phase 13) — deterministic
    trait scores + archetype, computed from real existing signals
    (never re-running any ML inference), plus a creative interpretation
    (real LLM call when available, an honest per-archetype demo
    fallback otherwise). Auto-computed and cached on first access;
    guest-accessible on a public cat, same visibility rule as every
    other analysis endpoint.
    """
    try:
        return await get_personality(db, analysis_id, viewer_user_id=user.id if user else None)
    except SourceAnalysisNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc


@router.post(
    "/{analysis_id}/personality/regenerate",
    response_model=CatPersonalityResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def regenerate_cat_personality(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> CatPersonalityResponse:
    """Regenerates only the creative interpretation — the structured
    trait scores and archetype are never touched (see
    `personality_service.regenerate_interpretation`'s docstring).
    Requires real ownership (not just public visibility): a mutating,
    potentially LLM-cost-bearing action, unlike the read-only GET above.
    """
    try:
        return await regenerate_interpretation(db, analysis_id, owner_user_id=user.id)
    except SourceAnalysisNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc
