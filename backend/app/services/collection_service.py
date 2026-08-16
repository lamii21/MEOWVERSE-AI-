import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import achievement_repository, event_repository, progress_repository
from app.repositories.analysis_repository import (
    get_breed_discovery_stats,
    get_discovered_breeds,
    get_distinct_color_names,
    get_rarity_distribution,
    get_user_stats,
)
from app.repositories.portrait_repository import count_distinct_user_styles, count_user_portraits
from app.repositories.story_repository import count_user_stories, has_story_of_style
from app.schemas.collection import AchievementOut, BreedDiscoveryOut, CollectionStats, ProgressOut
from app.schemas.story import StoryStyle
from app.services.achievement_definitions import ACHIEVEMENTS
from app.services.breed_catalog import get_supported_breeds
from app.services.progression import LevelProgress


async def _build_achievement_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Every number here comes from a real query scoped to `user_id` —
    unclaimed/guest analyses have `user_id IS NULL` and so are never
    counted, which is exactly the "never fabricate, never count demo
    data" contract the Phase 9 brief asks for (§15/§17): there's no
    separate "is this real" flag to check because unowned rows simply
    can't reach these queries in the first place.
    """
    raw = await get_user_stats(db, user_id)
    raw["distinct_colors"] = len(await get_distinct_color_names(db, user_id))
    raw["distinct_story_cats"] = await event_repository.count_events(
        db, user_id, "STORY_GENERATED"
    )
    raw["has_dreamy_story"] = await has_story_of_style(
        db, user_id, StoryStyle.DREAMY_EMOTIONAL.value
    )
    raw["total_portraits"] = await count_user_portraits(db, user_id)
    raw["distinct_portrait_styles"] = await count_distinct_user_styles(db, user_id)
    return raw


async def get_stats(db: AsyncSession, user_id: uuid.UUID) -> CollectionStats:
    raw = await get_user_stats(db, user_id)
    stories_created = await count_user_stories(db, user_id)
    unique_colors = len(await get_distinct_color_names(db, user_id))
    rarity_distribution = await get_rarity_distribution(db, user_id)

    supported_breeds = get_supported_breeds()
    discovered = await get_discovered_breeds(db, user_id)
    unique_breeds_discovered = len(discovered & set(supported_breeds))
    total_supported = len(supported_breeds)
    completion = (
        round(100 * unique_breeds_discovered / total_supported, 1) if total_supported else 0.0
    )

    return CollectionStats(
        total_cats=raw["total_cats"],
        favorite_breed=raw["favorite_breed"],
        most_common_color=raw["most_common_color"],
        legendary_count=raw["legendary_count"],
        rare_count=raw["rare_count"],
        favorites_count=raw["favorites_count"],
        stories_created=stories_created,
        unique_breeds_discovered=unique_breeds_discovered,
        total_supported_breeds=total_supported,
        completion_percentage=completion,
        unique_colors_discovered=unique_colors,
        rarity_distribution=rarity_distribution,
    )


async def sync_and_list_achievements(db: AsyncSession, user_id: uuid.UUID) -> list[AchievementOut]:
    """Compute-on-read: checks the user's real stats against every
    achievement definition and unlocks any newly-qualified ones, then
    returns the full list (locked and unlocked) for the UI. Cheap
    enough at this scale to run on every profile/achievements page
    load — no background job needed."""
    stats = await _build_achievement_stats(db, user_id)

    already_unlocked = await achievement_repository.get_unlocked_keys(db, user_id)
    for achievement in ACHIEVEMENTS:
        if achievement.key not in already_unlocked and achievement.is_unlocked(stats):
            await achievement_repository.unlock(db, user_id, achievement.key)

    unlocked_list = await achievement_repository.list_unlocked(db, user_id)
    unlocked_rows = {row.achievement_key: row for row in unlocked_list}

    results = []
    for a in ACHIEVEMENTS:
        current, target = a.progress(stats)
        results.append(
            AchievementOut(
                key=a.key,
                emoji=a.emoji,
                label=a.label,
                description=a.description,
                unlocked=a.key in unlocked_rows,
                unlocked_at=unlocked_rows[a.key].unlocked_at if a.key in unlocked_rows else None,
                progress_current=current,
                progress_target=target,
            )
        )
    return results


async def get_breed_explorer(db: AsyncSession, user_id: uuid.UUID) -> list[BreedDiscoveryOut]:
    """The full canonical breed universe (app/services/breed_catalog.py),
    each entry merged with this user's real per-breed stats where they
    exist — an undiscovered breed gets zeroed/None fields and
    `discovered=False`, never fabricated data pretending they've
    analyzed a breed they haven't (Phase 10 spec §10)."""
    per_breed = await get_breed_discovery_stats(db, user_id)
    return [
        BreedDiscoveryOut(
            breed=breed,
            discovered=breed in per_breed,
            count=per_breed.get(breed, {}).get("count", 0),
            best_confidence=per_breed.get(breed, {}).get("best_confidence"),
            latest_discovery=per_breed.get(breed, {}).get("latest_discovery"),
        )
        for breed in get_supported_breeds()
    ]


async def get_progress(db: AsyncSession, user_id: uuid.UUID) -> ProgressOut:
    xp = await progress_repository.get_xp(db, user_id)
    lp = LevelProgress(xp)
    return ProgressOut(
        xp=lp.xp,
        level=lp.level,
        level_title=lp.title,
        xp_into_level=lp.xp_into_level,
        xp_needed_for_level=lp.xp_needed_for_level,
        xp_for_next_level=lp.xp_for_next_level,
        progress_ratio=lp.progress_ratio,
    )
