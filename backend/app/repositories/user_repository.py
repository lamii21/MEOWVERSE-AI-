import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel


async def create_user(
    db: AsyncSession, *, email: str, password_hash: str, display_name: str
) -> UserModel:
    row = UserModel(email=email.lower(), password_hash=password_hash, display_name=display_name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    stmt = select(UserModel).where(UserModel.email == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    return await db.get(UserModel, user_id)


async def update_user(
    db: AsyncSession,
    user: UserModel,
    *,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> UserModel:
    if display_name is not None:
        user.display_name = display_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    return user
