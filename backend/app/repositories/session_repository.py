import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionModel


async def create_session(
    db: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expire_days: int
) -> SessionModel:
    row = SessionModel(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=expire_days),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_active_session_by_token_hash(
    db: AsyncSession, token_hash: str
) -> SessionModel | None:
    stmt = select(SessionModel).where(
        SessionModel.token_hash == token_hash,
        SessionModel.expires_at > datetime.now(UTC),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_session_by_token_hash(db: AsyncSession, token_hash: str) -> None:
    await db.execute(delete(SessionModel).where(SessionModel.token_hash == token_hash))
    await db.commit()
