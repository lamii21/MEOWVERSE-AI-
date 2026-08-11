"""The single place API routes call into to record a gamification
event (Phase 10 spec §13/§22): "a cat was discovered," "a cat was
favorited," "a story was generated," "a cat was shared." Turns that
into (idempotently) awarded XP, a possible level-up, and a possible
newly-unlocked achievement or two — all computed from real rows, never
trusted from the client.

Deliberately not a generic "event bus": five call sites (create_analysis
/save/favorite/share in analyses.py, create_story in stories.py) each
call `process_event` directly. A portfolio-scale project doesn't need
pub/sub machinery for five producers and one consumer.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import achievement_repository, event_repository, progress_repository
from app.schemas.gamification import GamificationEvent
from app.services.collection_service import sync_and_list_achievements
from app.services.progression import XP_VALUES, level_for_xp


async def _grant(db: AsyncSession, user_id: uuid.UUID, event_type: str, target_id: str) -> int:
    """Records the event if it's genuinely new (see
    CollectionEventModel's docstring for the anti-farming contract) and
    awards its XP exactly once. Returns the XP actually awarded (0 if
    this event had already happened before)."""
    amount = XP_VALUES[event_type]
    is_new = await event_repository.record_event_if_new(db, user_id, event_type, target_id, amount)
    if not is_new:
        return 0
    await progress_repository.add_xp(db, user_id, amount)
    return amount


async def process_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    target_id: uuid.UUID | str,
    *,
    is_new_breed: bool = False,
    is_new_rarity: bool = False,
) -> GamificationEvent:
    xp_before = await progress_repository.get_xp(db, user_id)
    level_before = level_for_xp(xp_before)

    xp_awarded = await _grant(db, user_id, event_type, str(target_id))

    before_keys = await achievement_repository.get_unlocked_keys(db, user_id)
    achievements = await sync_and_list_achievements(db, user_id)
    newly_unlocked = [a for a in achievements if a.unlocked and a.key not in before_keys]
    for achievement in newly_unlocked:
        xp_awarded += await _grant(db, user_id, "ACHIEVEMENT_UNLOCKED", achievement.key)

    total_xp = await progress_repository.get_xp(db, user_id)
    level_after = level_for_xp(total_xp)

    return GamificationEvent(
        xp_awarded=xp_awarded,
        total_xp=total_xp,
        level=level_after,
        leveled_up=level_after > level_before,
        is_new_breed=is_new_breed,
        is_new_rarity=is_new_rarity,
        newly_unlocked=newly_unlocked,
    )
