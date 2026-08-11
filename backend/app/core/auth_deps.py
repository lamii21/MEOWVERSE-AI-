from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import UserModel
from app.services.auth_service import get_user_from_session_token


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> UserModel | None:
    """Guest-friendly variant — returns None instead of raising, so the
    same endpoint (e.g. POST /api/v1/analyses) can serve both anonymous
    and logged-in callers and just branch on whether a user came back.
    """
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        return None
    return await get_user_from_session_token(db, token)


async def get_current_user(
    user: UserModel | None = Depends(get_current_user_optional),  # noqa: B008
) -> UserModel:
    """Hard-required variant for genuinely protected endpoints (collection,
    profile, favorite/unfavorite, save, logout). Covers all three of
    "missing session," "expired session," and "invalid/forged token" with
    the same 401 — get_user_from_session_token already returns None for
    all three, so there's nothing more specific (or leakable) to say.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user
