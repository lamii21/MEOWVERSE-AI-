import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.session import SessionModel
from app.models.user import UserModel
from app.repositories import session_repository, user_repository
from app.schemas.user import UserCreate, UserLogin


class EmailAlreadyRegisteredError(Exception):
    """Raised on duplicate registration — surfaced by the API layer as
    a 409, with a message that doesn't need to hide the email already
    exists (the user just typed it into the registration form
    themselves; this is different from the login-time "don't reveal
    whether an email exists" rule, which protects a stranger from
    probing someone else's account)."""


class InvalidCredentialsError(Exception):
    """Raised for both "no such user" and "wrong password" — the API
    layer must turn this into the exact same 401 message either way,
    so a caller can't use response differences to enumerate accounts."""


async def register_user(db: AsyncSession, data: UserCreate) -> UserModel:
    existing = await user_repository.get_user_by_email(db, data.email)
    if existing is not None:
        raise EmailAlreadyRegisteredError(data.email)

    password_hash = hash_password(data.password)
    return await user_repository.create_user(
        db, email=data.email, password_hash=password_hash, display_name=data.display_name
    )


async def authenticate_user(db: AsyncSession, data: UserLogin) -> UserModel:
    user = await user_repository.get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError()
    return user


async def create_session_for_user(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, SessionModel]:
    """Returns the raw token (goes in the cookie, never persisted) and
    the created session row (whose `token_hash` is what's actually
    stored)."""
    settings = get_settings()
    raw_token = generate_session_token()
    row = await session_repository.create_session(
        db,
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        expire_days=settings.session_expire_days,
    )
    return raw_token, row


async def get_user_from_session_token(db: AsyncSession, raw_token: str) -> UserModel | None:
    session = await session_repository.get_active_session_by_token_hash(
        db, hash_session_token(raw_token)
    )
    if session is None:
        return None
    return await user_repository.get_user(db, session.user_id)


async def logout(db: AsyncSession, raw_token: str) -> None:
    await session_repository.delete_session_by_token_hash(db, hash_session_token(raw_token))
