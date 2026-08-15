import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user_optional
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.models.user import UserModel
from app.schemas.explanation import CatExplanation
from app.services.explanation_service import (
    InvalidTargetClassError,
    SourceAnalysisNotVisibleError,
    get_explanation,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["explanation"])


class ExplanationRequest(BaseModel):
    """`target_class` is optional — defaults to the breed already shown
    to the user (spec §5). Only meaningful use of an explicit value:
    "why is this NOT a Persian" style curiosity; still validated
    against the classifier's real known classes, never an arbitrary
    string."""

    target_class: str | None = None


@router.post(
    "/{analysis_id}/explanation",
    response_model=CatExplanation,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_cat_explanation(
    analysis_id: uuid.UUID,
    body: ExplanationRequest = Body(default_factory=ExplanationRequest),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> CatExplanation:
    """"Why this breed?" (Phase 12) — generates (or reuses a cached)
    real Grad-CAM explanation. `POST`, not `GET`, because a cache miss
    genuinely creates new stored images and a new DB row — this isn't
    a pure read. Guest-accessible on a public analysis, same visibility
    rule as every other analysis endpoint; ownership is enforced inside
    `ExplanationService`, never assumed from the frontend route alone.

    Rate-limited (spec §30 concern: don't let this become an expensive
    unbounded compute endpoint) with the same general limiter as
    analysis/story generation — a cache hit is cheap, but a miss runs a
    real forward+backward pass through the classifier.
    """
    try:
        return await get_explanation(
            db,
            analysis_id,
            viewer_user_id=user.id if user else None,
            target_class=body.target_class,
        )
    except SourceAnalysisNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc
    except InvalidTargetClassError as exc:
        raise HTTPException(
            status_code=422, detail=f"'{exc}' isn't a breed this model recognizes."
        ) from exc
