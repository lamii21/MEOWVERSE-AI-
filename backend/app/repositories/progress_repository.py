import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import UserProgressModel


async def get_xp(db: AsyncSession, user_id: uuid.UUID) -> int:
    row = await db.get(UserProgressModel, user_id)
    return row.xp if row is not None else 0


async def add_xp(db: AsyncSession, user_id: uuid.UUID, amount: int) -> int:
    """Creates the progress row on first XP if it doesn't exist yet
    (ON CONFLICT DO NOTHING — a concurrent request racing to create the
    same row is harmless), then atomically increments `xp` in the
    database itself (`xp = xp + :amount`) rather than read-modify-write
    in Python, so two concurrent events for the same user can't clobber
    each other. Returns the new total.
    """
    await db.execute(
        pg_insert(UserProgressModel)
        .values(user_id=user_id, xp=0)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    stmt = (
        UserProgressModel.__table__.update()
        .where(UserProgressModel.user_id == user_id)
        .values(xp=UserProgressModel.xp + amount)
        .returning(UserProgressModel.xp)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
