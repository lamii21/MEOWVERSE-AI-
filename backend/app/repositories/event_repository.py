import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection_event import CollectionEventModel


async def record_event_if_new(
    db: AsyncSession, user_id: uuid.UUID, event_type: str, target_id: str, xp_awarded: int
) -> bool:
    """Insert-or-skip on the (user_id, event_type, target_id) unique
    constraint — this is the whole anti-farming mechanism (see
    CollectionEventModel's docstring). Returns True only if a new row
    was actually inserted, so the caller knows whether to grant XP.
    """
    stmt = (
        pg_insert(CollectionEventModel)
        .values(
            user_id=user_id,
            event_type=event_type,
            target_id=target_id,
            xp_awarded=xp_awarded,
        )
        .on_conflict_do_nothing(constraint="uq_collection_event")
        .returning(CollectionEventModel.id)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.first() is not None


async def count_events(db: AsyncSession, user_id: uuid.UUID, event_type: str) -> int:
    stmt = select(func.count()).where(
        CollectionEventModel.user_id == user_id, CollectionEventModel.event_type == event_type
    )
    return (await db.execute(stmt)).scalar_one()
