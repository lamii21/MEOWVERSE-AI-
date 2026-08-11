from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import get_current_user
from app.core.config import get_settings
from app.core.csrf import verify_same_origin
from app.core.database import get_db
from app.core.rate_limit import enforce_auth_rate_limit
from app.models.user import UserModel
from app.repositories.user_repository import update_user
from app.schemas.user import UserCreate, UserLogin, UserOut, UserUpdate
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_session_for_user,
    register_user,
)
from app.services.auth_service import logout as logout_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _to_user_out(user: UserModel) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_expire_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def register(
    body: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UserOut:
    try:
        user = await register_user(db, body)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=409, detail="An account with that email already exists."
        ) from exc

    token, _ = await create_session_for_user(db, user.id)
    _set_session_cookie(response, token)
    return _to_user_out(user)


@router.post("/login", response_model=UserOut, dependencies=[Depends(enforce_auth_rate_limit)])
async def login(
    body: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UserOut:
    try:
        user = await authenticate_user(db, body)
    except InvalidCredentialsError as exc:
        # Deliberately identical whether the email doesn't exist or the
        # password is wrong — see InvalidCredentialsError's docstring.
        raise HTTPException(status_code=401, detail="Incorrect email or password.") from exc

    token, _ = await create_session_for_user(db, user.id)
    _set_session_cookie(response, token)
    return _to_user_out(user)


@router.post("/logout", status_code=204, dependencies=[Depends(verify_same_origin)])
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await logout_service(db, token)
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: UserModel = Depends(get_current_user)) -> UserOut:  # noqa: B008
    return _to_user_out(user)


@router.patch("/me", response_model=UserOut, dependencies=[Depends(verify_same_origin)])
async def update_me(
    body: UserUpdate,
    user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UserOut:
    updated = await update_user(
        db, user, display_name=body.display_name, avatar_url=body.avatar_url
    )
    return _to_user_out(updated)
