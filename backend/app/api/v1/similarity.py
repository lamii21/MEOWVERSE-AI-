import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user_optional
from app.core.database import get_db
from app.models.user import UserModel
from app.schemas.similarity import SimilarityResponse
from app.services.similarity_service import SourceCatNotVisibleError, find_similar_cats

router = APIRouter(prefix="/api/v1/analyses", tags=["similarity"])


@router.get("/{analysis_id}/similar", response_model=SimilarityResponse)
async def get_similar_cats(
    analysis_id: uuid.UUID,
    k: int = Query(default=5, ge=1, le=20),
    breed: str | None = Query(default=None, max_length=100),
    rarity: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> SimilarityResponse:
    """"Cats Like This" (Phase 11). Guest-accessible, same visibility
    rule as `GET /api/v1/analyses/{id}` — the source cat must be public
    or owned by the caller; results are further scoped to public cats
    plus (if authenticated) the caller's own collection, applied inside
    `SimilarityService`, never here.

    `k` is hard-capped at 20 by the query parameter's own validation
    (`le=20`) — never trusts a larger client-supplied value (spec §12).

    `rarity`/`breed` are passed straight through, unvalidated against a
    fixed set — `SimilarityService` compares them against each
    candidate's real value (`row.rarity != rarity`), so a value that
    matches no real cat (a typo, an unrecognized rarity) naturally
    yields zero results rather than needing special-cased rejection or
    a silent fall-through to "no filter at all," which would be a
    confusing way for a typo'd filter to behave (spec §18: filters
    narrow results, they never get silently dropped).
    """
    try:
        return await find_similar_cats(
            db,
            analysis_id,
            viewer_user_id=user.id if user else None,
            k=k,
            breed=breed,
            rarity=rarity,
            favorites_only=favorites_only,
        )
    except SourceCatNotVisibleError as exc:
        raise HTTPException(status_code=404, detail="Cat not found.") from exc
