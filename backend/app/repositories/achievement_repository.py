import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import UserAchievementModel


async def get_unlocked_keys(db: AsyncSession, user_id: uuid.UUID) -> set[str]:
    stmt = select(UserAchievementModel.achievement_key).where(
        UserAchievementModel.user_id == user_id
    )
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def unlock(db: AsyncSession, user_id: uuid.UUID, achievement_key: str) -> None:
    # ON CONFLICT DO NOTHING on the (user_id, achievement_key) unique
    # constraint — sync_achievements already checks get_unlocked_keys
    # first, so this is belt-and-suspenders against a race between two
    # concurrent requests both trying to unlock the same achievement.
    stmt = (
        pg_insert(UserAchievementModel)
        .values(user_id=user_id, achievement_key=achievement_key)
        .on_conflict_do_nothing(constraint="uq_user_achievement")
    )
    await db.execute(stmt)
    await db.commit()


async def list_unlocked(db: AsyncSession, user_id: uuid.UUID) -> list[UserAchievementModel]:
    stmt = (
        select(UserAchievementModel)
        .where(UserAchievementModel.user_id == user_id)
        .order_by(UserAchievementModel.unlocked_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
