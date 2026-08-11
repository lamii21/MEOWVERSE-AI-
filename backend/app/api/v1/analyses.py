import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user, get_current_user_optional
from app.core.config import get_settings
from app.core.csrf import verify_same_origin
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.models.user import UserModel
from app.repositories.analysis_repository import (
    claim_analysis,
    get_analysis,
    get_owned_analysis,
    get_public_analysis,
    is_first_of_breed,
    is_first_of_rarity,
    set_favorite,
    set_private,
    set_public,
)
from app.repositories.story_repository import has_any_story
from app.schemas.analysis import AnalysisResult, BreedPrediction
from app.schemas.common import ColorSwatch
from app.schemas.gamification import GamificationEvent
from app.schemas.profile import CatProfile
from app.services.analysis_service import InvalidImageError, analyze_image
from app.services.gamification import process_event

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])

ACCEPTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _record_discovery(db: AsyncSession, user_id: uuid.UUID, row) -> GamificationEvent:
    """Shared by create_analysis (auto-owned) and save_cat (claimed):
    the moment an analysis first enters a user's collection is exactly
    the CAT_DISCOVERED event (Phase 10 spec §13), whichever of the two
    paths got it there. `is_first_of_breed`/`is_first_of_rarity` are
    computed *before* the event is recorded so "have I seen this breed
    before" correctly excludes the row currently being discovered."""
    is_new_breed = await is_first_of_breed(db, user_id, row.breed_label, row.id)
    is_new_rarity = await is_first_of_rarity(db, user_id, row.rarity, row.id)
    return await process_event(
        db,
        user_id,
        "CAT_DISCOVERED",
        row.id,
        is_new_breed=is_new_breed,
        is_new_rarity=is_new_rarity,
    )


def analysis_row_to_result(
    row, *, viewer_is_owner: bool, has_story: bool = False
) -> AnalysisResult:
    """`viewer_is_owner` is a required, explicit kwarg (no default) on
    purpose — every call site has to state which case it's in. `owned`
    and `is_favorite` are owner-only signals: a public /cat/[id] viewer
    must never learn whether (or by whom) a cat is favorited, or see an
    "owned" flag that a careless frontend could render as if it were
    *their own* — see Phase 9 spec §18, "public pages should expose
    only intended public information." `has_story` defaults to False
    (rather than being required) because most call sites here create a
    row that provably has no story yet; sites where it might already
    exist look it up explicitly and pass the real value.
    """
    return AnalysisResult(
        id=row.id,
        detected=True,
        breed=BreedPrediction(label=row.breed_label, confidence=row.breed_confidence),
        breed_mode=row.breed_mode,
        colors=[ColorSwatch.model_validate(c) for c in row.colors],
        colors_mode=row.colors_mode,
        embedding_available=False,
        profile=CatProfile.model_validate(row.profile),
        profile_mode=row.profile_mode,
        is_public=row.is_public,
        owned=viewer_is_owner,
        is_favorite=row.is_favorite if viewer_is_owner else False,
        image_url=row.image_url,
        created_at=row.created_at,
        has_story=has_story,
    )


@router.post(
    "",
    response_model=AnalysisResult,
    dependencies=[Depends(enforce_rate_limit)],
)
async def create_analysis(
    file: UploadFile = File(...),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> AnalysisResult:
    """Guest-accessible on purpose (Phase 9 spec §7: "guests should still
    be able to upload/analyze/view results"). If the request carries a
    valid session, the analysis is auto-owned by that user; otherwise it's
    created unowned and can be claimed later via POST .../save."""
    settings = get_settings()

    if file.content_type not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="MeowVerse needs a valid image.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    image_bytes = await file.read()
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"Image is too large — max {settings.max_upload_size_mb}MB.",
        )

    try:
        result = await analyze_image(
            image_bytes, file.content_type, db, user_id=user.id if user else None
        )
    except InvalidImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if user is not None and result.id is not None:
        row = await get_owned_analysis(db, result.id, user.id)
        if row is not None:
            result.gamification = await _record_discovery(db, user.id, row)
    return result


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> AnalysisResult:
    """Powers both the public /cat/[id] share page (Phase 8) and a
    signed-in owner viewing their own private cat's detail page (Phase
    9) — the same endpoint, because the visibility rule is exactly
    "public OR you own it," and duplicating this route per-caller-type
    would just be two places to keep an ownership check correct in.
    """
    row = await get_public_analysis(db, analysis_id)
    if row is not None:
        return analysis_row_to_result(
            row, viewer_is_owner=False, has_story=await has_any_story(db, row.id)
        )

    if user is not None:
        row = await get_owned_analysis(db, analysis_id, user.id)
        if row is not None:
            return analysis_row_to_result(
                row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
            )

    raise HTTPException(status_code=404, detail="Cat not found.")


@router.post(
    "/{analysis_id}/save",
    response_model=AnalysisResult,
    dependencies=[Depends(verify_same_origin)],
)
async def save_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> AnalysisResult:
    """The guest → account flow (Phase 9 spec §7/§28): a cat analyzed
    anonymously has no owner until this is called. Only works once per
    cat — an already-owned analysis (by this user or anyone else) can't
    be re-claimed, so this can't be used to "steal" someone else's cat
    by guessing its id.
    """
    row = await claim_analysis(db, analysis_id, user.id)
    if row is None:
        existing = await get_analysis(db, analysis_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Cat not found.")
        raise HTTPException(status_code=409, detail="This cat has already been saved.")
    result = analysis_row_to_result(
        row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
    )
    result.gamification = await _record_discovery(db, user.id, row)
    return result


@router.post(
    "/{analysis_id}/favorite",
    response_model=AnalysisResult,
    dependencies=[Depends(verify_same_origin)],
)
async def favorite_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> AnalysisResult:
    row = await set_favorite(db, analysis_id, user.id, True)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    result = analysis_row_to_result(
        row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
    )
    result.gamification = await process_event(db, user.id, "CAT_FAVORITED", row.id)
    return result


@router.post(
    "/{analysis_id}/unfavorite",
    response_model=AnalysisResult,
    dependencies=[Depends(verify_same_origin)],
)
async def unfavorite_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> AnalysisResult:
    row = await set_favorite(db, analysis_id, user.id, False)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    return analysis_row_to_result(
        row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
    )


@router.post(
    "/{analysis_id}/share",
    response_model=AnalysisResult,
    dependencies=[Depends(verify_same_origin)],
)
async def share_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> AnalysisResult:
    """Flips an analysis to public so its /cat/[id] Cat Card becomes
    viewable. Idempotent, only ever triggered by an explicit "Share"
    click — never automatic. Phase 9: now requires the caller to own
    the cat (previously unauthenticated/unowned, Phase 8) — a private
    resource must never be publishable by anyone other than its owner.
    """
    row = await set_public(db, analysis_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    result = analysis_row_to_result(
        row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
    )
    result.gamification = await process_event(db, user.id, "CAT_SHARED", row.id)
    return result


@router.post(
    "/{analysis_id}/unshare",
    response_model=AnalysisResult,
    dependencies=[Depends(verify_same_origin)],
)
async def unshare_cat(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> AnalysisResult:
    row = await set_private(db, analysis_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    return analysis_row_to_result(
        row, viewer_is_owner=True, has_story=await has_any_story(db, row.id)
    )
