from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AchievementDefinition:
    key: str
    emoji: str
    label: str
    description: str
    # Given the same `stats` dict `collection_service.get_user_stats`
    # builds (real counts from the DB — never demo data, since
    # unclaimed/guest analyses have no user_id and so never enter these
    # queries at all), returns whether the achievement should be unlocked.
    is_unlocked: Callable[[dict], bool]


ACHIEVEMENTS: list[AchievementDefinition] = [
    AchievementDefinition(
        key="first_meow",
        emoji="🐾",
        label="First Meow",
        description="Save your first cat to your collection.",
        is_unlocked=lambda stats: stats["total_cats"] >= 1,
    ),
    AchievementDefinition(
        key="cat_explorer",
        emoji="🌸",
        label="Cat Explorer",
        description="Save 5 cats to your collection.",
        is_unlocked=lambda stats: stats["total_cats"] >= 5,
    ),
    AchievementDefinition(
        key="collector",
        emoji="💎",
        label="Collector",
        description="Save 15 cats to your collection.",
        is_unlocked=lambda stats: stats["total_cats"] >= 15,
    ),
    AchievementDefinition(
        key="rainbow_collector",
        emoji="🌈",
        label="Rainbow Collector",
        description="Discover cats spanning 5 distinct fur colors.",
        is_unlocked=lambda stats: stats["distinct_colors"] >= 5,
    ),
    AchievementDefinition(
        key="legendary_hunter",
        emoji="👑",
        label="Legendary Hunter",
        description="Discover a Legendary or Mythical cat.",
        is_unlocked=lambda stats: stats["legendary_count"] >= 1,
    ),
]

ACHIEVEMENTS_BY_KEY = {a.key: a for a in ACHIEVEMENTS}
