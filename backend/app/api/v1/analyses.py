import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.repositories.analysis_repository import get_public_analysis, set_public
from app.schemas.analysis import AnalysisResult, BreedPrediction
from app.schemas.common import ColorSwatch
from app.schemas.profile import CatProfile
from app.services.analysis_service import InvalidImageError, analyze_image

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])

ACCEPTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _row_to_result(row) -> AnalysisResult:
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
    )


@router.post(
    "",
    response_model=AnalysisResult,
    dependencies=[Depends(enforce_rate_limit)],
)
async def create_analysis(
    file: UploadFile = File(...),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AnalysisResult:
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
        return await analyze_image(image_bytes, db)
    except InvalidImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_public_cat(
    analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> AnalysisResult:
    """Powers the public /cat/[id] Cat Card share page (Phase 8). An
    analysis is private by default — this 404s until the owner
    explicitly shares it via POST .../share below, same contract as
    the story share endpoint from Phase 7.
    """
    row = await get_public_analysis(db, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    return _row_to_result(row)


@router.post("/{analysis_id}/share", response_model=AnalysisResult)
async def share_cat(
    analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> AnalysisResult:
    """Flips an analysis to public so its /cat/[id] Cat Card becomes
    viewable. Idempotent, only ever triggered by an explicit "Share"
    click — never automatic. No auth/ownership system yet (Phase 9),
    same intentionally-unauthenticated stance as every other
    analysis/story endpoint in this project so far.
    """
    row = await set_public(db, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Cat not found.")
    return _row_to_result(row)
