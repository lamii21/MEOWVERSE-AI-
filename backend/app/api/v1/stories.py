import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user, get_current_user_optional
from app.core.csrf import verify_same_origin
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.models.user import UserModel
from app.repositories.story_repository import (
    get_owned_story,
    get_public_story,
    set_private,
    set_public,
)
from app.schemas.story import CatStory, StoryRequest, StoryResponse, StoryStyle
from app.services.story_service import AnalysisNotFoundError, get_or_generate_story

router = APIRouter(tags=["stories"])


def _to_response(row) -> StoryResponse:
    return StoryResponse(
        id=row.id,
        analysis_id=row.analysis_id,
        style=StoryStyle(row.style),
        story=CatStory.model_validate(row.story),
        story_mode=row.story_mode,
        provider=row.provider,
        is_public=row.is_public,
        created_at=row.created_at,
    )


@router.post(
    "/api/v1/analyses/{analysis_id}/story",
    response_model=StoryResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def create_story(
    analysis_id: uuid.UUID,
    body: StoryRequest = Body(default_factory=StoryRequest),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StoryResponse:
    """Returns the existing story for (analysis_id, style) unless
    `regenerate: true` is explicitly requested — see
    app/services/story_service.py for the cost-control contract.

    Guest-accessible on purpose (Phase 9 spec §7) — story generation
    doesn't require auth, same as analysis creation.
    """
    try:
        row = await get_or_generate_story(db, analysis_id, body.style, body.regenerate)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No analysis found with that id.") from exc

    return _to_response(row)


@router.get("/api/v1/stories/{story_id}", response_model=StoryResponse)
async def get_story_by_id(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> StoryResponse:
    """Powers the public /story/[id] share page (Phase 7 §17) and, as of
    Phase 9, a signed-in owner viewing their own private story — same
    "public OR you own it" rule as GET /api/v1/analyses/{id}.
    """
    row = await get_public_story(db, story_id)
    if row is not None:
        return _to_response(row)

    if user is not None:
        row = await get_owned_story(db, story_id, user.id)
        if row is not None:
            return _to_response(row)

    raise HTTPException(status_code=404, detail="Story not found.")


@router.post(
    "/api/v1/stories/{story_id}/share",
    response_model=StoryResponse,
    dependencies=[Depends(verify_same_origin)],
)
async def share_story(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> StoryResponse:
    """Flips a story to public so its /story/[id] page becomes viewable.
    Idempotent, and only ever triggered by an explicit "Share" click —
    never automatic. Phase 9: now requires the caller to own the
    story's parent analysis (previously unauthenticated, Phase 7).
    """
    row = await set_public(db, story_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Story not found.")

    return _to_response(row)


@router.post(
    "/api/v1/stories/{story_id}/unshare",
    response_model=StoryResponse,
    dependencies=[Depends(verify_same_origin)],
)
async def unshare_story(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user: UserModel = Depends(get_current_user),  # noqa: B008
) -> StoryResponse:
    row = await set_private(db, story_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Story not found.")

    return _to_response(row)
