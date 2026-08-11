import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import achievement_repository
from app.repositories.analysis_repository import get_distinct_color_names, get_user_stats
from app.repositories.story_repository import count_user_stories
from app.schemas.collection import AchievementOut, CollectionStats
from app.services.achievement_definitions import ACHIEVEMENTS


async def get_stats(db: AsyncSession, user_id: uuid.UUID) -> CollectionStats:
    """Every number here comes from a real query scoped to `user_id` —
    unclaimed/guest analyses have `user_id IS NULL` and so are never
    counted, which is exactly the "never fabricate, never count demo
    data" contract the Phase 9 brief asks for (§15/§17): there's no
    separate "is this real" flag to check because unowned rows simply
    can't reach these queries in the first place.
    """
    raw = await get_user_stats(db, user_id)
    stories_created = await count_user_stories(db, user_id)
    return CollectionStats(
        total_cats=raw["total_cats"],
        favorite_breed=raw["favorite_breed"],
        most_common_color=raw["most_common_color"],
        legendary_count=raw["legendary_count"],
        favorites_count=raw["favorites_count"],
        stories_created=stories_created,
    )


async def sync_and_list_achievements(db: AsyncSession, user_id: uuid.UUID) -> list[AchievementOut]:
    """Compute-on-read: checks the user's real stats against every
    achievement definition and unlocks any newly-qualified ones, then
    returns the full list (locked and unlocked) for the UI. Cheap
    enough at this scale to run on every profile/achievements page
    load — no background job needed."""
    stats = await get_user_stats(db, user_id)
    stats["distinct_colors"] = len(await get_distinct_color_names(db, user_id))

    already_unlocked = await achievement_repository.get_unlocked_keys(db, user_id)
    for achievement in ACHIEVEMENTS:
        if achievement.key not in already_unlocked and achievement.is_unlocked(stats):
            await achievement_repository.unlock(db, user_id, achievement.key)

    unlocked_list = await achievement_repository.list_unlocked(db, user_id)
    unlocked_rows = {row.achievement_key: row for row in unlocked_list}

    return [
        AchievementOut(
            key=a.key,
            emoji=a.emoji,
            label=a.label,
            description=a.description,
            unlocked=a.key in unlocked_rows,
            unlocked_at=unlocked_rows[a.key].unlocked_at if a.key in unlocked_rows else None,
        )
        for a in ACHIEVEMENTS
    ]
