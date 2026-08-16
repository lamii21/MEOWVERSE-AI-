import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user, get_current_user_optional
from app.core.csrf import verify_same_origin
from app.core.database import get_db
from app.core.rate_limit import enforce_portrait_rate_limit, enforce_rate_limit
from app.models.user import UserModel
from app.schemas.portrait import PortraitGenerateRequest, PortraitListResponse, PortraitOut
from app.services.gamification import process_event
from app.services.portrait_service import (
    PortraitNotVisibleError,
    SourceAnalysisNotVisibleError,
    generate_portrait,
    get_portrait,
    list_portraits,
    share_portrait,
    unshare_portrait,
)

router = APIRouter(tags=["portrait"])


@router.get(
    "/api/v1/analyses/{analysis_id}/portraits",
    response_model=PortraitListResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_cat_portraits(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> PortraitListResponse:
    """AI Cat Portrait Studio (Phase 14) — every portrait generated so
    far for this cat. Guest-accessible on a public cat (public,
    succeeded portraits only); the owner sees everything, including
    failed attempts and private portraits.
    """
    try:
        portraits = await list_portraits(db, analysis_id, viewer_user_id=user.id if user else None)
    except SourceAnalysisNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc
    return PortraitListResponse(portraits=portraits)


@router.post(
    "/api/v1/analyses/{analysis_id}/portraits",
    response_model=PortraitOut,
    dependencies=[Depends(enforce_portrait_rate_limit), Depends(verify_same_origin)],
)
async def create_cat_portrait(
    analysis_id: uuid.UUID,
    body: PortraitGenerateRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> PortraitOut:
    """Generates one AI portrait in the requested style. Owner-only —
    unlike GET above, there is no "public OR owned" path here at all: a
    stranger who can merely view a public cat must never be able to
    trigger a real, cost-bearing image generation against it (spec §9).
    Reuses an existing identical, already-succeeded generation unless
    `force_new` is set (spec §23 "Generate Again"). Behind a stricter,
    generation-specific rate limit than the general AI endpoints (spec
    §24) — real image generation is meaningfully more expensive than a
    text completion.
    """
    try:
        result = await generate_portrait(
            db,
            analysis_id,
            owner_user_id=user.id,
            style=body.style,
            customization=body.customization,
            force_new=body.force_new,
        )
    except SourceAnalysisNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc

    if result.status == "succeeded" and not result.reused:
        # Keyed on this portrait's own id: a reused result (identical
        # request replayed) never re-grants XP, but every genuinely new
        # succeeded portrait — including repeated "Generate Again" calls
        # in the same style — does, same as Storyteller's per-story XP.
        result.gamification = await process_event(db, user.id, "PORTRAIT_GENERATED", result.id)

    return result


@router.get(
    "/api/v1/portraits/{portrait_id}",
    response_model=PortraitOut,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_portrait_by_id(
    portrait_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> PortraitOut:
    """Powers the public `/portrait/[id]` share page and an owner
    viewing their own portrait directly — same "public OR you own it"
    rule as GET /api/v1/analyses/{id} and GET /api/v1/stories/{id}.
    """
    try:
        return await get_portrait(db, portrait_id, viewer_user_id=user.id if user else None)
    except PortraitNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Portrait not found.") from exc


@router.post(
    "/api/v1/portraits/{portrait_id}/share",
    response_model=PortraitOut,
    dependencies=[Depends(verify_same_origin)],
)
async def share_cat_portrait(
    portrait_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> PortraitOut:
    """Flips a portrait to public so its `/portrait/[id]` page becomes
    viewable — an explicit act, never automatic, same pattern as
    stories' share endpoint (Phase 7/9)."""
    try:
        return await share_portrait(db, portrait_id, owner_user_id=user.id)
    except PortraitNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Portrait not found.") from exc


@router.post(
    "/api/v1/portraits/{portrait_id}/unshare",
    response_model=PortraitOut,
    dependencies=[Depends(verify_same_origin)],
)
async def unshare_cat_portrait(
    portrait_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> PortraitOut:
    try:
        return await unshare_portrait(db, portrait_id, owner_user_id=user.id)
    except PortraitNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Portrait not found.") from exc
